import asyncio
from pyrogram import Client, filters
from pyrogram.session import Session

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Хранилище состояний
user_states = {}

@app.on_message(filters.private & filters.command("start"))
async def start(c, m):
    chat_id = m.chat.id
    if chat_id in user_states and user_states[chat_id].get("logged"):
        await m.reply("✅ Ты уже вошёл! Используй /spam @username")
        return
    
    await m.reply("📱 Отправь номер телефона в формате +79991234567")
    user_states[chat_id] = {"step": "wait_number"}

@app.on_message(filters.private & filters.regex(r"^\+\d{10,15}$"))
async def get_number(c, m):
    chat_id = m.chat.id
    if chat_id not in user_states:
        await m.reply("❌ Нажми /start сначала")
        return
    
    number = m.text.strip()
    try:
        # Используем in_memory=True — НЕТ ФАЙЛОВ, НЕТ ОШИБОК БД
        client = Client(
            f"user_{chat_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        await client.start()
        sent = await client.send_code(number)
        
        user_states[chat_id] = {
            "step": "wait_code",
            "client": client,
            "number": number,
            "phone_code_hash": sent.phone_code_hash
        }
        await m.reply(f"✅ Код отправлен на {number}\nВведи код цифрами:")
    except Exception as e:
        await m.reply(f"❌ Ошибка: {str(e)[:150]}\nПопробуй ещё раз")

@app.on_message(filters.private & filters.regex(r"^\d{4,6}$"))
async def get_code(c, m):
    chat_id = m.chat.id
    if chat_id not in user_states:
        await m.reply("❌ Нажми /start сначала")
        return
    
    state = user_states[chat_id]
    if state.get("step") != "wait_code":
        await m.reply("❌ Сначала отправь номер")
        return
    
    code = m.text.strip()
    client = state["client"]
    
    try:
        await client.sign_in(
            phone_number=state["number"],
            phone_code_hash=state["phone_code_hash"],
            phone_code=code
        )
        user_states[chat_id]["step"] = "logged"
        user_states[chat_id]["logged"] = True
        await m.reply("✅ Вход выполнен! Теперь /spam @username")
    except Exception as e:
        await m.reply(f"❌ Ошибка: {str(e)[:150]}")

@app.on_message(filters.private & filters.command("spam"))
async def start_spam(c, m):
    chat_id = m.chat.id
    if chat_id not in user_states or not user_states[chat_id].get("logged"):
        await m.reply("❌ Сначала войди через /start")
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        await m.reply("⚠️ /spam @username")
        return
    
    target = parts[1].strip()
    client = user_states[chat_id]["client"]
    
    try:
        target_user = await client.get_users(target)
        await m.reply(f"🍪 Спам {target_user.first_name} печеньем!")
        
        count = 0
        while True:
            await client.send_message(target_user.id, "🍪" * 20)
            count += 1
            await asyncio.sleep(0.3)
            if count % 20 == 0:
                await m.reply(f"📨 {count} пачек")
    except Exception as e:
        await m.reply(f"❌ Ошибка: {str(e)[:150]}")

if __name__ == "__main__":
    app.run()
