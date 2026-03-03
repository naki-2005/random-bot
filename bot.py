import requests
import time
import threading
import json
import os
import random
import argparse
from datetime import datetime

TOKEN = ""
BOT_MASTER = ""
BOT_MASTER_ID = 0
start_msg = ""
REPO = ""
BARER = ""

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--token", help="Token del bot", default="")
    parser.add_argument("-master", "--master", help="Master @usuario,ID", default="")
    parser.add_argument("-msg", "--message", help="Mensaje de start", default="")
    parser.add_argument("-repo", "--repo", help="Repo usuario/repo", default="")
    parser.add_argument("-barer", "--barer", help="Token de GitHub", default="")
    return parser.parse_args()

args = get_args()
TOKEN = args.token
if args.master and "," in args.master:
    parts = args.master.split(",")
    BOT_MASTER = parts[0]
    try:
        BOT_MASTER_ID = int(parts[1])
    except:
        BOT_MASTER_ID = 0
start_msg = args.message
REPO = args.repo
BARER = args.barer

ADMINS_FILE = "admins.json"
FRIENDS_FILE = "friends.json"
QUOTES_FILE = "quotes.json"
BANNED_FILE = "banned.json"

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

def save_to_github(filename, repo_path, message):
    if not REPO or not BARER:
        return
    
    import urllib.request
    import base64
    import json as json_lib
    
    url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}"
    headers = {
        "Authorization": f"Bearer {BARER}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-urllib"
    }
    
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            existing = json_lib.loads(response.read())
            sha = existing.get("sha")
    except:
        pass
    
    with open(filename, "rb") as f:
        encoded_content = base64.b64encode(f.read()).decode("utf-8")
    
    payload = {
        "message": message,
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
    
    req = urllib.request.Request(
        url,
        data=json_lib.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="PUT"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return
    except:
        return

def save_admins():
    save_data(ADMINS_FILE, admins)
    save_to_github(ADMINS_FILE, f"data/{ADMINS_FILE}", "Actualización de admins")

def save_friends():
    save_data(FRIENDS_FILE, friends)
    save_to_github(FRIENDS_FILE, f"data/{FRIENDS_FILE}", "Actualización de friends")

def save_quotes():
    save_data(QUOTES_FILE, quotes)
    save_to_github(QUOTES_FILE, f"data/{QUOTES_FILE}", "Actualización de quotes")

def save_banned():
    save_data(BANNED_FILE, banned_users)
    save_to_github(BANNED_FILE, f"data/{BANNED_FILE}", "Actualización de banned")

admins = load_data(ADMINS_FILE)
if BOT_MASTER_ID and BOT_MASTER_ID not in admins:
    admins.append(BOT_MASTER_ID)
    save_admins()

friends = load_data(FRIENDS_FILE)
quotes = load_data(QUOTES_FILE)
banned_users = load_data(BANNED_FILE)

def is_admin(user_id):
    return user_id == BOT_MASTER_ID or user_id in admins

def is_friend(user_id):
    return user_id in friends or is_admin(user_id)

def is_banned(user_id):
    return user_id in banned_users

def set_my_commands():
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"
    commands = [
        {"command": "start", "description": "Iniciar el bot"},
        {"command": "friends", "description": "Agregar/quitar amigos (admin)"},
        {"command": "admin", "description": "Agregar/quitar admins (solo master)"},
        {"command": "ban", "description": "Banear usuario (admin+)"},
        {"command": "quote", "description": "Guardar mensaje (friends+)"},
        {"command": "random", "description": "Obtener mensaje aleatorio"},
        {"command": "help", "description": "Ayuda"}
    ]
    data = {"commands": commands}
    requests.post(url, json=data)

def send_message(chat_id, text, reply_to=None):
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_to:
        data["reply_parameters"] = {"message_id": reply_to}
    requests.post(url, json=data)

def react_to_message(chat_id, message_id, emoji):
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/setMessageReaction"
    data = {"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]}
    requests.post(url, json=data)

def forward_message(from_chat_id, message_id, original_chat_id, original_message_id):
    if not TOKEN or not BOT_MASTER_ID:
        return
    if from_chat_id == BOT_MASTER_ID or is_banned(from_chat_id):
        react_to_message(original_chat_id, original_message_id, "🚫")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
    data = {"chat_id": BOT_MASTER_ID, "from_chat_id": from_chat_id, "message_id": message_id}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        result = response.json()
        if result["ok"]:
            react_to_message(original_chat_id, original_message_id, "👌")

def copy_message(from_chat_id, message_id, to_chat_id):
    if not TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TOKEN}/copyMessage"
    data = {"chat_id": to_chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    response = requests.post(url, data=data)
    return response.json() if response.status_code == 200 else None

def get_chat_member(user_id):
    if not TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TOKEN}/getChat"
    data = {"chat_id": user_id}
    response = requests.post(url, data=data)
    return response.json() if response.status_code == 200 else None

def add_or_remove_user(command, user_input, from_user_id):
    global admins, friends
    
    if not user_input:
        send_message(from_user_id, "Debes especificar un @usuario o ID")
        return
    
    user_id = None
    username = None
    
    if str(user_input).startswith("@"):
        username = user_input
        chat_info = get_chat_member(user_input)
        if chat_info and chat_info.get("ok"):
            user_id = chat_info["result"]["id"]
        else:
            send_message(from_user_id, f"No se puede acceder a {user_input}. El usuario debe iniciar el bot primero.")
            return
    else:
        try:
            user_id = int(user_input)
            chat_info = get_chat_member(user_id)
            if not (chat_info and chat_info.get("ok")):
                send_message(from_user_id, f"El usuario {user_id} debe iniciar el bot primero.")
                return
        except:
            send_message(from_user_id, "Formato inválido. Usa @usuario o ID numérico")
            return
    
    target_list = friends if command == "/friends" else admins
    
    if command == "/admin" and from_user_id != BOT_MASTER_ID:
        send_message(from_user_id, "Solo el master puede gestionar admins")
        return
    
    if command == "/friends" and not is_admin(from_user_id):
        send_message(from_user_id, "Solo admins pueden gestionar amigos")
        return
    
    if user_id == BOT_MASTER_ID:
        send_message(from_user_id, "No puedes modificar al master")
        return
    
    if user_id in target_list:
        target_list.remove(user_id)
        action = "eliminado de"
    else:
        target_list.append(user_id)
        action = "agregado a"
    
    if command == "/admin":
        save_admins()
    else:
        save_friends()
    
    list_name = "admins" if command == "/admin" else "amigos"
    send_message(from_user_id, f"Usuario {user_input} {action} la lista de {list_name}")

def handle_ban(command, user_input, from_user_id):
    global banned_users
    
    if not is_admin(from_user_id):
        send_message(from_user_id, "No tienes permiso para usar /ban")
        return
    
    if not user_input:
        send_message(from_user_id, "Debes especificar un @usuario o ID")
        return
    
    user_id = None
    
    if str(user_input).startswith("@"):
        username = user_input
        chat_info = get_chat_member(user_input)
        if chat_info and chat_info.get("ok"):
            user_id = chat_info["result"]["id"]
        else:
            send_message(from_user_id, f"No se puede acceder a {user_input}")
            return
    else:
        try:
            user_id = int(user_input)
        except:
            send_message(from_user_id, "Formato inválido. Usa @usuario o ID numérico")
            return
    
    if user_id == BOT_MASTER_ID or is_admin(user_id):
        send_message(from_user_id, "No puedes banear al master o a un admin")
        return
    
    if user_id in banned_users:
        banned_users.remove(user_id)
        action = "desbaneado"
    else:
        banned_users.append(user_id)
        action = "baneado"
    
    save_banned()
    send_message(from_user_id, f"Usuario {user_input} ha sido {action}")

def handle_quote(message, chat_id, user_id):
    if is_banned(user_id):
        send_message(chat_id, "Estás baneado del bot", message["message_id"])
        return
    
    if not is_friend(user_id) and user_id != BOT_MASTER_ID:
        send_message(chat_id, "No tienes permiso para usar /quote", message["message_id"])
        return
    
    if "reply_to_message" not in message:
        send_message(chat_id, "Este comando debe usarse en respuesta a un mensaje", message["message_id"])
        return
    
    reply_msg = message["reply_to_message"]
    from_chat_id = reply_msg["chat"]["id"]
    msg_id = reply_msg["message_id"]
    
    result = copy_message(from_chat_id, msg_id, BOT_MASTER_ID)
    
    if result and result.get("ok"):
        first_name = message["from"].get("first_name", "Anónimo")
        quote_data = {
            "message_id": result["result"]["message_id"],
            "chat_id": BOT_MASTER_ID,
            "first_name": first_name,
            "date": datetime.now().isoformat()
        }
        quotes.append(quote_data)
        save_quotes()
        send_message(chat_id, "✅ Mensaje guardado en quotes", message["message_id"])
        react_to_message(chat_id, message["message_id"], "👍")
    else:
        send_message(chat_id, "❌ Error al guardar el mensaje", message["message_id"])

def handle_random(message, chat_id, user_id):
    if is_banned(user_id):
        send_message(chat_id, "Estás baneado del bot", message["message_id"])
        return
    
    if not quotes:
        send_message(chat_id, "No hay quotes disponibles")
        return
    
    quote = random.choice(quotes)
    
    result = copy_message(quote["chat_id"], quote["message_id"], chat_id)
    
    if result and result.get("ok"):
        send_message(chat_id, f"By: {quote['first_name']}")
    else:
        quotes.remove(quote)
        save_quotes()
        send_message(chat_id, "El quote ya no está disponible")

def handle_update(update):
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    if "text" in message:
        text = message["text"]
        
        if text == "/start":
            send_message(chat_id, start_msg)
        
        elif text.startswith("/friends"):
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            add_or_remove_user("/friends", user_input, user_id)
        
        elif text.startswith("/admin"):
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            add_or_remove_user("/admin", user_input, user_id)
        
        elif text.startswith("/ban"):
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            handle_ban("/ban", user_input, user_id)
        
        elif text == "/quote":
            handle_quote(message, chat_id, user_id)
        
        elif text == "/random":
            handle_random(message, chat_id, user_id)
        
        elif text == "/help":
            help_text = (
                "/start - Iniciar bot\n"
                "/friends @usuario/ID - Gestionar amigos (admins)\n"
                "/admin @usuario/ID - Gestionar admins (solo master)\n"
                "/ban @usuario/ID - Banear/desbanear (admin+)\n"
                "/quote - Guardar mensaje respondiendo (friends+)\n"
                "/random - Quote aleatorio\n"
                "/help - Esta ayuda"
            )
            send_message(chat_id, help_text)
        
        elif chat_id != BOT_MASTER_ID and not is_banned(user_id):
            forward_message(chat_id, message["message_id"], chat_id, message["message_id"])
    
    elif chat_id != BOT_MASTER_ID and not is_banned(user_id):
        forward_message(chat_id, message["message_id"], chat_id, message["message_id"])

def get_updates(offset=None):
    if not TOKEN:
        return {"ok": False, "result": []}
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset, "allowed_updates": ["message"]}
    response = requests.get(url, params=params)
    return response.json()

def main():
    if TOKEN:
        set_my_commands()
    offset = None
    while True:
        try:
            result = get_updates(offset)
            if result.get("ok"):
                for update in result["result"]:
                    offset = update["update_id"] + 1
                    threading.Thread(target=handle_update, args=(update,)).start()
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
