import asyncio
import requests
import time
import threading
import json
import os
import random
import argparse
from datetime import datetime
from telethon import TelegramClient, events
import base64
import urllib.request

TOKEN = ""
BOT_MASTER = ""
BOT_MASTER_ID = 0
start_msg = ""
REPO = ""
BARER = ""
BOT_CHANNEL = ""
API_ID = 0
API_HASH = ""

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--token", help="Token del bot", default="")
    parser.add_argument("-master", "--master", help="Master @usuario,ID", default="")
    parser.add_argument("-msg", "--message", help="Mensaje de start", default="")
    parser.add_argument("-repo", "--repo", help="Repo usuario/repo", default="")
    parser.add_argument("-barer", "--barer", help="Token de GitHub", default="")
    parser.add_argument("-bc", "--botchannel", help="Canal del bot @channel,-ID", default="")
    parser.add_argument("-api", "--api_id", help="API ID de Telegram", default="")
    parser.add_argument("-hash", "--api_hash", help="API Hash de Telegram", default="")
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
BOT_CHANNEL = args.botchannel
API_ID = int(args.api_id) if args.api_id else 0
API_HASH = args.api_hash

ADMINS_FILE = "admins.json"
FRIENDS_FILE = "friends.json"
QUOTES_FILE = "quotes.json"
BANNED_FILE = "banned.json"
DM_DISABLED_FILE = "dm_disabled.json"

client = TelegramClient('bot_session', API_ID, API_HASH)

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
            existing = json.loads(response.read())
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
        data=json.dumps(payload).encode("utf-8"),
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

def save_dm_disabled():
    save_data(DM_DISABLED_FILE, dm_disabled_users)
    save_to_github(DM_DISABLED_FILE, f"data/{DM_DISABLED_FILE}", "Actualización de DM disabled")

admins = load_data(ADMINS_FILE)
if BOT_MASTER_ID and BOT_MASTER_ID not in admins:
    admins.append(BOT_MASTER_ID)
    save_admins()

friends = load_data(FRIENDS_FILE)
quotes = load_data(QUOTES_FILE)
banned_users = load_data(BANNED_FILE)
dm_disabled_users = load_data(DM_DISABLED_FILE)

def is_admin(user_id):
    return user_id == BOT_MASTER_ID or user_id in admins

def is_friend(user_id):
    return user_id in friends or is_admin(user_id)

def is_banned(user_id):
    return user_id in banned_users

def is_dm_disabled(user_id):
    return user_id in dm_disabled_users

# Funciones con requests para la API de Telegram
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

def get_chats():
    if not TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 0, "allowed_updates": ["message"]}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            chats = set()
            for update in result["result"]:
                if "message" in update:
                    chat = update["message"]["chat"]
                    chat_id = chat["id"]
                    if chat_id > 0 and chat_id != BOT_MASTER_ID:
                        chats.add(chat_id)
            return list(chats)
    return []

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
        {"command": "post", "description": "Publicar en canal (friends+)"},
        {"command": "postdm", "description": "Enviar a todos los chats (friends+)"},
        {"command": "toggledm", "description": "Activar/desactivar reenvío DM"},
        {"command": "random", "description": "Obtener mensaje aleatorio"},
        {"command": "info", "description": "Información del bot (admin+)"},
        {"command": "help", "description": "Ayuda"}
    ]
    data = {"commands": commands}
    requests.post(url, json=data)

@events.register(events.NewMessage)
async def handler(event):
    if not event.message:
        return
    
    chat = await event.get_chat()
    chat_id = chat.id
    user_id = event.sender_id
    
    if not user_id:
        return
    
    if chat_id != BOT_MASTER_ID and not is_banned(user_id):
        if not is_dm_disabled(user_id):
            url = f"https://api.telegram.org/bot{TOKEN}/forwardMessage"
            data = {
                "chat_id": BOT_MASTER_ID,
                "from_chat_id": chat_id,
                "message_id": event.message.id
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    react_to_message(chat_id, event.message.id, "👌")
        else:
            react_to_message(chat_id, event.message.id, "🔇")
    
    if event.message.text:
        text = event.message.text
        
        if text == "/start":
            send_message(chat_id, start_msg)
        
        elif text.startswith("/friends"):
            if not is_admin(user_id):
                return
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            if user_input:
                target_id = None
                if str(user_input).startswith("@"):
                    chat_info = get_chat_member(user_input)
                    if chat_info and chat_info.get("ok"):
                        target_id = chat_info["result"]["id"]
                else:
                    try:
                        target_id = int(user_input)
                    except:
                        pass
                
                if target_id and target_id != BOT_MASTER_ID:
                    if target_id in friends:
                        friends.remove(target_id)
                    else:
                        friends.append(target_id)
                    save_friends()
        
        elif text.startswith("/admin"):
            if user_id != BOT_MASTER_ID:
                return
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            if user_input:
                target_id = None
                if str(user_input).startswith("@"):
                    chat_info = get_chat_member(user_input)
                    if chat_info and chat_info.get("ok"):
                        target_id = chat_info["result"]["id"]
                else:
                    try:
                        target_id = int(user_input)
                    except:
                        pass
                
                if target_id and target_id != BOT_MASTER_ID:
                    if target_id in admins:
                        admins.remove(target_id)
                    else:
                        admins.append(target_id)
                    save_admins()
        
        elif text.startswith("/ban"):
            if not is_admin(user_id):
                return
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            if user_input:
                target_id = None
                if str(user_input).startswith("@"):
                    chat_info = get_chat_member(user_input)
                    if chat_info and chat_info.get("ok"):
                        target_id = chat_info["result"]["id"]
                else:
                    try:
                        target_id = int(user_input)
                    except:
                        pass
                
                if target_id and target_id != BOT_MASTER_ID and not is_admin(target_id):
                    if target_id in banned_users:
                        banned_users.remove(target_id)
                    else:
                        banned_users.append(target_id)
                    save_banned()
        
        elif text == "/quote":
            if is_banned(user_id):
                return
            if not is_friend(user_id) and user_id != BOT_MASTER_ID:
                return
            
            if event.message.reply_to_msg_id:
                reply_msg = await event.message.get_reply_message()
                if reply_msg:
                    result = copy_message(chat_id, reply_msg.id, BOT_MASTER_ID)
                    if result and result.get("ok"):
                        first_name = event.sender.first_name or "Anónimo"
                        quote_data = {
                            "message_id": result["result"]["message_id"],
                            "chat_id": BOT_MASTER_ID,
                            "first_name": first_name,
                            "date": datetime.now().isoformat()
                        }
                        quotes.append(quote_data)
                        save_quotes()
                        send_message(chat_id, "✅ Mensaje guardado en quotes", event.message.id)
                        react_to_message(chat_id, event.message.id, "👍")
                    else:
                        send_message(chat_id, "❌ Error al guardar el mensaje", event.message.id)
            else:
                send_message(chat_id, "Este comando debe usarse en respuesta a un mensaje", event.message.id)
        
        elif text == "/post":
            if is_banned(user_id):
                return
            if not is_friend(user_id) and user_id != BOT_MASTER_ID:
                return
            if not BOT_CHANNEL:
                send_message(chat_id, "No hay canal configurado", event.message.id)
                return
            
            if event.message.reply_to_msg_id:
                reply_msg = await event.message.get_reply_message()
                if reply_msg:
                    channel_id = BOT_CHANNEL
                    if channel_id.startswith('@'):
                        channel_info = get_chat_member(channel_id)
                        if channel_info and channel_info.get("ok"):
                            channel_id = channel_info["result"]["id"]
                    
                    result = copy_message(chat_id, reply_msg.id, channel_id)
                    if result and result.get("ok"):
                        first_name = event.sender.first_name or "Anónimo"
                        send_message(channel_id, f"By: {first_name}")
                        send_message(chat_id, "✅ Mensaje publicado en el canal", event.message.id)
                        react_to_message(chat_id, event.message.id, "👍")
                    else:
                        send_message(chat_id, "❌ Error al publicar el mensaje", event.message.id)
            else:
                send_message(chat_id, "Este comando debe usarse en respuesta a un mensaje", event.message.id)
        
        elif text == "/postdm":
            if is_banned(user_id):
                return
            if not is_friend(user_id) and user_id != BOT_MASTER_ID:
                return
            
            if event.message.reply_to_msg_id:
                reply_msg = await event.message.get_reply_message()
                if reply_msg:
                    chats = get_chats()
                    first_name = event.sender.first_name or "Anónimo"
                    sent_count = 0
                    
                    for chat in chats:
                        if chat != BOT_MASTER_ID:
                            result = copy_message(chat_id, reply_msg.id, chat)
                            if result and result.get("ok"):
                                send_message(chat, f"By: {first_name}")
                                sent_count += 1
                            time.sleep(0.1)
                    
                    send_message(chat_id, f"✅ Mensaje enviado a {sent_count} chats", event.message.id)
                    react_to_message(chat_id, event.message.id, "👍")
            else:
                send_message(chat_id, "Este comando debe usarse en respuesta a un mensaje", event.message.id)
        
        elif text == "/toggledm":
            if is_banned(user_id):
                return
            
            if user_id in dm_disabled_users:
                dm_disabled_users.remove(user_id)
                status = "activado"
            else:
                dm_disabled_users.append(user_id)
                status = "desactivado"
            
            save_dm_disabled()
            send_message(chat_id, f"✅ Reenvío de mensajes {status}", event.message.id)
            react_to_message(chat_id, event.message.id, "👍")
        
        elif text == "/random":
            if is_banned(user_id):
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
        
        elif text == "/info":
            if is_banned(user_id):
                return
            if not is_admin(user_id):
                return
            
            chats = get_chats()
            send_message(chat_id, f"El bot tiene {len(chats)} chats", event.message.id)
        
        elif text == "/help":
            help_text = (
                "/start - Iniciar bot\n"
                "/friends @usuario/ID - Gestionar amigos (admins)\n"
                "/admin @usuario/ID - Gestionar admins (solo master)\n"
                "/ban @usuario/ID - Banear/desbanear (admin+)\n"
                "/quote - Guardar mensaje respondiendo (friends+)\n"
                "/post - Publicar en canal respondiendo (friends+)\n"
                "/postdm - Enviar a todos los chats respondiendo (friends+)\n"
                "/toggledm - Activar/desactivar reenvío DM\n"
                "/random - Quote aleatorio\n"
                "/info - Información del bot (admin+)\n"
                "/help - Esta ayuda"
            )
            send_message(chat_id, help_text)

async def main():
    await client.start(bot_token=TOKEN)
    print("✅ Bot iniciado correctamente")
    
    set_my_commands()
    
    client.add_event_handler(handler)
    
    await client.run_until_disconnected()

def run_bot():
    asyncio.run(main())

if __name__ == "__main__":
    run_bot()
