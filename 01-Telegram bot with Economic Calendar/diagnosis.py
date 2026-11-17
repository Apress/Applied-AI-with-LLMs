from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("api_id"))
api_hash = os.getenv("api_hash")
session_name = os.getenv("session_name")

client = TelegramClient(session_name, api_id, api_hash)

async def list_chats():
    async for dialog in client.iter_dialogs():
        name = dialog.name
        id = dialog.id
        entity = type(dialog.entity).__name__
        print(f"🔹 {name} | ID: {id} | TYPE: {entity}")

with client:
    client.loop.run_until_complete(list_chats())
