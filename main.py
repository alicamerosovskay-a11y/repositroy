import asyncio
import os
import logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import PhoneCodeInvalidError, PhoneCodeExpiredError
import random

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

# Логи
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs("sessions", exist_ok=True)

user_states = {}
spam_tasks = {}  # {chat_id: [task1, task2, ...]}

async def main():
    bot = await TelegramClient("sessions/bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    logger.info("🚀 МЕГА-БОТ ЗАПУЩЕН НА ВИЛЛЕ В ЧАДЕ!")
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        chat_id = event.chat_id
        if chat_id in user_states and user_states[chat_id].get('logged'):
            await event.reply('✅ Уже в системе! /spam @username1 @username2 ...')
            return
        buttons = [[Button.request_phone('📱 Передать контакт', resize=True)]]
        await event.reply('Нажми кнопку для входа:', buttons=buttons)
        user_states[chat_id] = {'step': 'wait_contact'}

    @bot.on(events.NewMessage(func=lambda e: e.contact))
    async def get_contact(event):
        chat_id = event.chat_id
        if chat_id not in user_states:
            await event.reply('❌ /start')
            return
        phone = event.contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
        try:
            client = TelegramClient(f"sessions/user_{chat_id}", API_ID, API_HASH)
            await client.connect()
            result = await client.send_code_request(phone)
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
                'code': '',
                'targets': []  # Список целей
            }
            await event.reply(f'✅ Код на {phone}. Введи через кнопки:', buttons=keyboard)
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
            await event.answer('Сначала контакт', alert=True)
            return
        if data == '✅ Готово':
            code = state['code']
            if len(code) < 4:
                await event.answer('4-6 цифр', alert=True)
                return
            try:
                await state['client'].sign_in(
                    phone=state['phone'],
                    code=code,
                    phone_code_hash=state['phone_code_hash']
                )
                state['step'] = 'logged'
                state['logged'] = True
                await event.edit('✅ Вход выполнен!\nТеперь /spam @user1 @user2 @user3')
            except Exception as e:
                await event.answer(f'Ошибка: {str(e)[:50]}', alert=True)
                state['code'] = ''
            return
        if data == '⬅️':
            state['code'] = state['code'][:-1]
        else:
            if len(state['code']) >= 6:
                await event.answer('Макс 6', alert=True)
                return
            state['code'] += data
        current = state['code']
        display = '•' * len(current) if current else '____'
        await event.edit(
            f'Код: **{display}** ({len(current)}/6)',
            buttons=keyboard_buttons()
        )

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
            await event.reply('❌ Сначала войди')
            return
        
        # Если спам уже идёт — останавливаем
        if chat_id in spam_tasks:
            for task in spam_tasks[chat_id]:
                if not task.done():
                    task.cancel()
            await event.reply('🔄 Остановил старый спам. Запускаю новый...')
        
        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply('⚠️ /spam @user1 @user2 @user3 ...')
            return
        
        targets = parts[1:]
        state = user_states[chat_id]
        state['targets'] = targets
        client = state['client']
        
        # Проверяем всех юзеров
        users = []
        for t in targets:
            try:
                user = await client.get_entity(t)
                users.append(user)
            except Exception as e:
                await event.reply(f'❌ Не найден {t}: {str(e)[:50]}')
                return
        
        await event.reply(f'🍪 Запускаю спам для {len(users)} аккаунтов! (по 1 сообщению, очень быстро)')
        
        # ЗАПУСКАЕМ МНОГОЗАДАЧНОСТЬ — ДЛЯ КАЖДОГО АККАУНТА СВОЙ ПОТОК
        tasks = []
        for user in users:
            task = asyncio.create_task(spam_loop(event, chat_id, user, client))
            tasks.append(task)
        
        spam_tasks[chat_id] = tasks
        logger.info(f"🍪 Запущен спам для {len(users)} аккаунтов (chat_id: {chat_id})")

    async def spam_loop(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                # ОТПРАВЛЯЕМ ПО 1 СООБЩЕНИЮ
                await client.send_message(target_user, '🍪')
                count += 1
                
                # ОЧЕНЬ БЫСТРО — 0.05 СЕКУНДЫ
                await asyncio.sleep(0.05)
                
                # Каждые 100 сообщений — отчёт
                if count % 100 == 0:
                    await event.reply(f'📨 {target_user.first_name}: {count} сообщений')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name}: остановлен (отправлено {count})')
            logger.info(f"🛑 Спам остановлен для {target_user.first_name} (отправлено: {count})")
        except Exception as e:
            await event.reply(f'❌ {target_user.first_name}: ошибка {str(e)[:50]}')
            logger.error(f"Ошибка спама для {target_user.first_name}: {e}")

    @bot.on(events.NewMessage(pattern='/stop'))
    async def stop_spam(event):
        chat_id = event.chat_id
        if chat_id not in spam_tasks:
            await event.reply('❌ Спам не запущен')
            return
        for task in spam_tasks[chat_id]:
            if not task.done():
                task.cancel()
        await event.reply('🛑 Все спам-потоки остановлены!')
        del spam_tasks[chat_id]

    @bot.on(events.NewMessage(pattern='/help'))
    async def help_command(event):
        await event.reply(
            '📖 **Команды:**\n'
            '/start — вход\n'
            '/spam @user1 @user2 @user3 — спам для многих\n'
            '/stop — остановить всё\n'
            '/help — помощь\n'
            '🚀 Скорость: 0.05 сек между сообщениями\n'
            '👥 Многопоточность: каждый аккаунт в своём потоке'
        )

    print('🚀 МЕГА-БОТ ГОТОВ! ВИЛЛА В ЧАДЕ, ПЛОВ, ХЛЕБ, СПАМ!')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
