import asyncio
from pyrogram import Client, filters

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Храним состояния прямо в памяти (для Railway норм, пока не перезагрузится)
temp_clients = {}

@app.on_message(filters.private & filters.command("start"))
async def start(c, m):
    chat_id = m.chat.id
    # Если уже есть клиент — не создаём новый
    if chat_id in temp_clients:
        await m.reply("👋 Ты уже авторизован. Отправь /spam @username")
        return
    
    await m.reply("📱 Отправь номер с кодом страны (например +79991234567)")
    client = Client(f"sessions/{chat_id}", api_id=API_ID, api_hash=API_HASH)
    await client.start()
    temp_clients[chat_id] = {"client": client, "step": "wait_number"}

@app.on_message(filters.private & filters.regex(r"^\+\d{7,15}$"))
async def handle_number(c, m):
    chat_id = m.chat.id
    if chat_id not in temp_clients:
        await m.reply("❌ Сначала /start")
        return
    
    data = temp_clients[chat_id]
    client = data["client"]
    number = m.text.strip()
    
    try:
        sent = await client.send_code(number)
        data["number"] = number
        data["phone_code_hash"] = sent.phone_code_hash
        data["step"] = "wait_code"
        await m.reply(f"✅ Код отправлен на {number}. Введи код (только цифры)")
    except Exception as e:
        await m.reply(f"❌ Ошибка при отправке кода: {e}")

@app.on_message(filters.private & filters.regex(r"^\d{4,6}$"))
async def handle_code(c, m):
    chat_id = m.chat.id
    if chat_id not in temp_clients:
        await m.reply("❌ Сначала /start")
        return
    
    data = temp_clients[chat_id]
    client = data["client"]
    code = m.text.strip()
    
    try:
        await client.sign_in(
            phone_number=data["number"],
            phone_code_hash=data["phone_code_hash"],
            phone_code=code
        )
        await m.reply("✅ Вход выполнен! Теперь отправь /spam @username")
        data["step"] = "logged"
    except Exception as e:
        await m.reply(f"❌ Неверный код или ошибка: {e}")

@app.on_message(filters.private & filters.command("spam"))
async def spam(c, m):
    chat_id = m.chat.id
    if chat_id not in temp_clients:
        await m.reply("❌ Сначала /start и войди")
        return
    
    data = temp_clients[chat_id]
    if data.get("step") != "logged":
        await m.reply("❌ Ты ещё не вошёл. Отправь номер и код.")
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        await m.reply("⚠️ Пример: /spam @username")
        return
    
    target = parts[1].strip()
    client = data["client"]
    
    try:
        target_user = await client.get_users(target)
        await m.reply(f"🔁 Начинаю спам {target_user.first_name} печеньем 🍪")
        count = 0
        while True:
            await client.send_message(target_user.id, "🍪" * 20)
            count += 1
            await asyncio.sleep(0.3)
            if count % 30 == 0:
                await m.reply(f"📨 Отправлено {count} пачек")
    except Exception as e:
        await m.reply(f"❌ Ошибка при спаме: {e}")

if __name__ == "__main__":
    app.run()
