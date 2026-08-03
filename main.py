import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import MemorySession

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

# Бот
bot = TelegramClient(MemorySession(), API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Храним состояния пользователей
user_states = {}

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    chat_id = event.chat_id
    if chat_id in user_states and user_states[chat_id].get('logged'):
        await event.reply('✅ Ты уже вошёл! Используй /spam @username')
        return
    await event.reply('📱 Отправь номер телефона в формате +79991234567')
    user_states[chat_id] = {'step': 'wait_number'}

@bot.on(events.NewMessage(pattern=r'^\+\d{10,15}$'))
async def get_number(event):
    chat_id = event.chat_id
    if chat_id not in user_states:
        await event.reply('❌ Нажми /start сначала')
        return
    
    number = event.raw_text.strip()
    try:
        # Создаём КЛИЕНТ ПОЛЬЗОВАТЕЛЯ в памяти
        client = TelegramClient(MemorySession(), API_ID, API_HASH)
        await client.start()
        sent = await client.send_code_request(number)
        
        user_states[chat_id] = {
            'step': 'wait_code',
            'client': client,
            'number': number,
            'phone_code_hash': sent.phone_code_hash
        }
        await event.reply(f'✅ Код отправлен на {number}\nВведи код цифрами:')
    except Exception as e:
        await event.reply(f'❌ Ошибка: {str(e)[:150]}')

@bot.on(events.NewMessage(pattern=r'^\d{4,6}$'))
async def get_code(event):
    chat_id = event.chat_id
    if chat_id not in user_states:
        await event.reply('❌ Нажми /start сначала')
        return
    
    state = user_states[chat_id]
    if state.get('step') != 'wait_code':
        await event.reply('❌ Сначала отправь номер')
        return
    
    code = event.raw_text.strip()
    client = state['client']
    
    try:
        await client.sign_in(
            phone=state['number'],
            code=code,
            phone_code_hash=state['phone_code_hash']
        )
        user_states[chat_id]['step'] = 'logged'
        user_states[chat_id]['logged'] = True
        await event.reply('✅ Вход выполнен! Теперь /spam @username')
    except Exception as e:
        await event.reply(f'❌ Ошибка: {str(e)[:150]}')

@bot.on(events.NewMessage(pattern='/spam'))
async def start_spam(event):
    chat_id = event.chat_id
    if chat_id not in user_states or not user_states[chat_id].get('logged'):
        await event.reply('❌ Сначала войди через /start')
        return
    
    parts = event.raw_text.split()
    if len(parts) < 2:
        await event.reply('⚠️ Пример: /spam @username')
        return
    
    target = parts[1].strip()
    client = user_states[chat_id]['client']
    
    try:
        target_user = await client.get_entity(target)
        await event.reply(f'🍪 Спам {target_user.first_name} печеньем!')
        
        count = 0
        while True:
            await client.send_message(target_user, '🍪' * 20)
            count += 1
            await asyncio.sleep(0.3)
            if count % 20 == 0:
                await event.reply(f'📨 Отправлено {count} пачек')
    except Exception as e:
        await event.reply(f'❌ Ошибка спама: {str(e)[:150]}')

print('🍪 БОТ ЗАПУЩЕН НА TELETHON!')
bot.run_until_disconnected()
