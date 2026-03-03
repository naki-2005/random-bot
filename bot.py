import asyncio
import time
import threading
import json
import os
import random
import argparse
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault, MessageEntityBotCommand
from telethon.errors import FloodWaitError
import base64
import urllib.request
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch

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

async def set_my_commands():
    if not client:
        return
    commands = [
        BotCommand(command="start", description="Iniciar el bot"),
        BotCommand(command="friends", description="Agregar/quitar amigos (admin)"),
        BotCommand(command="admin", description="Agregar/quitar admins (solo master)"),
        BotCommand(command="ban", description="Banear usuario (admin+)"),
        BotCommand(command="quote", description="Guardar mensaje (friends+)"),
        BotCommand(command="post", description="Publicar en canal (friends+)"),
        BotCommand(command="postdm", description="Enviar a todos los chats (friends+)"),
        BotCommand(command="toggledm", description="Activar/desactivar reenvío DM"),
        BotCommand(command="random", description="Obtener mensaje aleatorio"),
        BotCommand(command="info", description="Información del bot (admin+)"),
        BotCommand(command="help", description="Ayuda")
    ]
    try:
        await client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='',
            commands=commands
        ))
    except:
        pass

async def get_chat_member(user_identifier):
    try:
        if str(user_identifier).startswith('@'):
            entity = await client.get_entity(user_identifier)
            return entity.id
        else:
            return int(user_identifier)
    except:
        return None

async def get_all_chats():
    chats = []
    async for dialog in client.iter_dialogs():
        if dialog.is_user and dialog.id != BOT_MASTER_ID:
            chats.append(dialog.id)
    return chats

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@events.register(events.NewMessage)
async def handler(event):
    if not event.message:
        return
    
    chat = await event.get_chat()
    chat_id = chat.id
    user_id = event.sender_id
    
    if not user_id:
        return
    
    if event.message.text:
        text = event.message.text
        
        if text == "/start":
            await event.respond(start_msg)
        
        elif text.startswith("/friends"):
            if not is_admin(user_id):
                return
            parts = text.split(maxsplit=1)
            user_input = parts[1] if len(parts) > 1 else None
            if user_input:
                target_id = await get_chat_member(user_input)
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
                target_id = await get_chat_member(user_input)
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
                target_id = await get_chat_member(user_input)
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
                    forwarded = await client.send_message(BOT_MASTER_ID, reply_msg)
                    if forwarded:
                        first_name = event.sender.first_name or "Anónimo"
                        quote_data = {
                            "message_id": forwarded.id,
                            "chat_id": BOT_MASTER_ID,
                            "first_name": first_name,
                            "date": datetime.now().isoformat()
                        }
                        quotes.append(quote_data)
                        save_quotes()
                        await event.respond("✅ Mensaje guardado en quotes")
                        await event.message.react("👍")
            else:
                await event.respond("Este comando debe usarse en respuesta a un mensaje")
        
        elif text == "/post":
            if is_banned(user_id):
                return
            if not is_friend(user_id) and user_id != BOT_MASTER_ID:
                return
            if not BOT_CHANNEL:
                await event.respond("No hay canal configurado")
                return
            if event.message.reply_to_msg_id:
                reply_msg = await event.message.get_reply_message()
                if reply_msg:
                    try:
                        channel_id = int(BOT_CHANNEL) if BOT_CHANNEL.lstrip('-').isdigit() else BOT_CHANNEL
                        await client.send_message(channel_id, reply_msg)
                        first_name = event.sender.first_name or "Anónimo"
                        await client.send_message(channel_id, f"By: {first_name}")
                        await event.respond("✅ Mensaje publicado en el canal")
                        await event.message.react("👍")
                    except:
                        await event.respond("❌ Error al publicar el mensaje")
            else:
                await event.respond("Este comando debe usarse en respuesta a un mensaje")
        
        elif text == "/postdm":
            if is_banned(user_id):
                return
            if not is_friend(user_id) and user_id != BOT_MASTER_ID:
                return
            if event.message.reply_to_msg_id:
                reply_msg = await event.message.get_reply_message()
                if reply_msg:
                    chats = await get_all_chats()
                    first_name = event.sender.first_name or "Anónimo"
                    sent_count = 0
                    for chat_id in chats:
                        try:
                            await client.send_message(chat_id, reply_msg)
                            await client.send_message(chat_id, f"By: {first_name}")
                            sent_count += 1
                            await asyncio.sleep(0.1)
                        except:
                            continue
                    await event.respond(f"✅ Mensaje enviado a {sent_count} chats")
                    await event.message.react("👍")
            else:
                await event.respond("Este comando debe usarse en respuesta a un mensaje")
        
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
            await event.respond(f"✅ Reenvío de mensajes {status}")
            await event.message.react("👍")
        
        elif text == "/random":
            if is_banned(user_id):
                return
            if not quotes:
                await event.respond("No hay quotes disponibles")
                return
            quote = random.choice(quotes)
            try:
                msg = await client.get_messages(quote["chat_id"], ids=quote["message_id"])
                if msg:
                    await client.send_message(chat_id, msg)
                    await client.send_message(chat_id, f"By: {quote['first_name']}")
                else:
                    quotes.remove(quote)
                    save_quotes()
                    await event.respond("El quote ya no está disponible")
            except:
                quotes.remove(quote)
                save_quotes()
                await event.respond("El quote ya no está disponible")
        
        elif text == "/info":
            if is_banned(user_id):
                return
            if not is_admin(user_id):
                return
            chats = await get_all_chats()
            await event.respond(f"El bot tiene {len(chats)} chats")
        
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
            await event.respond(help_text)
        
        elif chat_id != BOT_MASTER_ID and not is_banned(user_id):
            if not is_dm_disabled(user_id):
                try:
                    await client.send_message(BOT_MASTER_ID, event.message)
                    await event.message.react("👌")
                except:
                    pass
            else:
                await event.message.react("🔇")
    
    elif chat_id != BOT_MASTER_ID and not is_banned(user_id):
        if not is_dm_disabled(user_id):
            try:
                await client.send_message(BOT_MASTER_ID, event.message)
                await event.message.react("👌")
            except:
                pass
        else:
            await event.message.react("🔇")

async def main():
    await client.start(bot_token=TOKEN)
    print("Bot iniciado correctamente")
    client.add_event_handler(handler)
    await set_my_commands()
    await client.run_until_disconnected()

def start_bot():
    asyncio.run(main())

if __name__ == "__main__":
    start_bot()
