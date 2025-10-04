import os
import logging
import sqlite3
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Твой токен
BOT_TOKEN = "8419033501:AAECCXZBqUeHTBs-EvF7dr5bm-mt2Cd6vQQ"

# Твой ID админа
ADMIN_IDS = [7871625571]

# Пакеты Telegram Stars
STAR_PACKAGES = {
    "50": {"stars": 50, "price": 79},
    "100": {"stars": 100, "price": 156},
    "200": {"stars": 200, "price": 311},
    "300": {"stars": 300, "price": 465},
    "400": {"stars": 400, "price": 620},
    "500": {"stars": 500, "price": 775},
    "600": {"stars": 600, "price": 930},
    "700": {"stars": 700, "price": 1085}
}

# Реквизиты для разных банков
BANK_DETAILS = {
    "sber": {
        "name": "Сбербанк",
        "card_number": "2202 2082 1248 1809",
        "recipient": "АРТЁМ Р",
        "color": "🟢",
        "description": "Перевод по номеру карты"
    },
    "tinkoff": {
        "name": "Тинькофф", 
        "card_number": "5536 9140 0907 1360",
        "recipient": "АРТЁМ Р",
        "color": "🟡",
        "description": "Перевод по номеру карты"
    }
}

# Генерация номера заказа
def generate_order_id():
    return random.randint(100000, 999999)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('stars.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number INTEGER UNIQUE,
            user_id INTEGER,
            user_name TEXT,
            user_username TEXT,
            package TEXT,
            stars INTEGER,
            price INTEGER,
            bank_selected TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Отправка уведомления админу о новом заказе
async def notify_admin(context, order_data):
    order_number = order_data['order_number']
    user_name = order_data['user_name']
    user_username = order_data['user_username']
    stars = order_data['stars']
    price = order_data['price']
    user_id = order_data['user_id']
    bank = order_data['bank']
    
    bank_info = BANK_DETAILS.get(bank, BANK_DETAILS["sber"])
    
    message = (
        f"🎉 **НОВЫЙ ЗАКАЗ!**\n\n"
        f"📦 Номер заказа: `{order_number}`\n"
        f"👤 Пользователь: {user_name}\n"
        f"📱 Username: @{user_username if user_username else 'нет'}\n"
        f"🆔 ID: `{user_id}`\n"
        f"⭐ Stars: {stars}\n"
        f"💵 Сумма: {price} руб\n"
        f"🏦 Банк: {bank_info['name']}\n"
        f"⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
        f"💳 **Реквизиты для перевода:**\n"
        f"Банк: {bank_info['name']}\n"
        f"Карта: `{bank_info['card_number']}`\n"
        f"Получатель: {bank_info['recipient']}\n"
        f"Сумма: {price} руб\n"
        f"📝 Комментарий: `{order_number}`"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            keyboard = [
                [InlineKeyboardButton("📨 Написать пользователю", url=f"tg://user?id={user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                admin_id,
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Ошибка отправки админу {admin_id}: {e}")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Купить Stars", callback_data="buy_stars")],
        [InlineKeyboardButton("📊 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Добро пожаловать в магазин Telegram Stars! 🌟\n\n"
        f"✅ **АВТОМАТИЧЕСКАЯ ВЫДАЧА**\n"
        f"⚡ Мгновенное получение после оплаты\n"
        f"💳 Оплата по номеру карты (Сбер, Тинькофф)\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Показать пакеты Stars
async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for package_id, package in STAR_PACKAGES.items():
        button = InlineKeyboardButton(
            f"{package['stars']} Stars - {package['price']} руб",
            callback_data=f"package_{package_id}"
        )
        keyboard.append([button])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎁 Выберите пакет Stars:\n\n💡 *Stars приходят автоматически после оплаты*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Выбор банка после выбора пакета
async def select_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    package_id = query.data.replace("package_", "")
    context.user_data['selected_package'] = package_id
    
    keyboard = [
        [InlineKeyboardButton(f"🟢 Сбербанк", callback_data=f"bank_sber_{package_id}")],
        [InlineKeyboardButton(f"🟡 Тинькофф", callback_data=f"bank_tinkoff_{package_id}")],
        [InlineKeyboardButton("🔙 Назад к пакетам", callback_data="buy_stars")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏦 **Выберите банк для оплаты:**\n\n"
        "Оплата осуществляется по номеру карты",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Создание заказа после выбора банка
async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Получаем данные из callback
    data_parts = query.data.split('_')
    bank = data_parts[1]  # sber, tinkoff
    package_id = data_parts[2]
    
    package = STAR_PACKAGES[package_id]
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    user_username = query.from_user.username
    
    # Генерируем номер заказа
    order_number = generate_order_id()
    
    # Создаем заказ в базе
    conn = sqlite3.connect('stars.db')
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO orders (order_number, user_id, user_name, user_username, package, stars, price, bank_selected) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (order_number, user_id, user_name, user_username, package_id, package['stars'], package['price'], bank)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        order_number = generate_order_id()
        cursor.execute(
            'INSERT INTO orders (order_number, user_id, user_name, user_username, package, stars, price, bank_selected) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (order_number, user_id, user_name, user_username, package_id, package['stars'], package['price'], bank)
        )
        conn.commit()
    finally:
        conn.close()
    
    # Отправляем уведомление админу
    order_data = {
        'order_number': order_number,
        'user_id': user_id,
        'user_name': user_name,
        'user_username': user_username,
        'stars': package['stars'],
        'price': package['price'],
        'bank': bank
    }
    
    await notify_admin(context, order_data)
    
    # Показываем инструкцию пользователю
    bank_info = BANK_DETAILS[bank]
    
    message = (
        f"📦 **Ваш заказ #{order_number}**\n\n"
        f"⭐ Пакет: {package['stars']} Stars\n"
        f"💵 Стоимость: {package['price']} руб\n"
        f"🏦 Банк: {bank_info['name']}\n\n"
        f"💳 **Оплата по номеру карты:**\n"
        f"1. Откройте приложение вашего банка\n"
        f"2. Выберите 'Перевод по номеру карты'\n"
        f"3. Введите номер карты: `{bank_info['card_number']}`\n"
        f"4. Сумма: `{package['price']}` руб\n"
        f"5. **Комментарий: `{order_number}`**\n\n"
        f"👤 **Получатель:** {bank_info['recipient']}\n\n"
        f"🔔 **После оплаты:**\n"
        f"✅ *Stars придут автоматически в течение 1-2 минут*\n"
        f"• При проблемах пишите @M1rnes\n\n"
        f"💡 *Обязательно укажите комментарий {order_number}*"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("🔄 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Мои заказы
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    conn = sqlite3.connect('stars.db')
    cursor = conn.cursor()
    cursor.execute('SELECT order_number, stars, price, status, bank_selected, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        await query.edit_message_text("📭 У вас пока нет заказов.")
        return
    
    orders_text = "📊 **Ваши заказы:**\n\n"
    for order in orders:
        order_number, stars, price, status, bank, created_at = order
        bank_info = BANK_DETAILS.get(bank, {"name": "Не указан", "color": "⚫"})
        
        if status == 'completed':
            status_icon = "✅"
            status_text = "Выполнен"
        elif status == 'cancelled':
            status_icon = "❌"
            status_text = "Отменен"
        else:
            status_icon = "⏳"
            status_text = "Ожидает оплаты"
        
        orders_text += f"{status_icon} Заказ #{order_number}\n"
        orders_text += f"⭐ {stars} Stars - {price} руб\n"
        orders_text += f"🏦 Банк: {bank_info['name']}\n"
        orders_text += f"📊 Статус: {status_text}\n"
        orders_text += f"📅 {created_at[:16]}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(orders_text, reply_markup=reply_markup, parse_mode='Markdown')

# Главное меню
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⭐ Купить Stars", callback_data="buy_stars")],
        [InlineKeyboardButton("📊 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Добро пожаловать в магазин Telegram Stars! 🌟\n\n"
        f"✅ **АВТОМАТИЧЕСКАЯ ВЫДАЧА**\n"
        f"⚡ Мгновенное получение после оплаты\n"
        f"💳 Оплата по номеру карты (Сбер, Тинькофф)\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Помощь
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    banks_list = "\n".join([f"• {bank['color']} {bank['name']} - {bank['description']}" for bank in BANK_DETAILS.values()])
    
    help_text = (
        f"ℹ️ **Помощь по боту:**\n\n"
        f"⭐ **Как купить Stars:**\n"
        f"1. Нажмите 'Купить Stars'\n"
        f"2. Выберите пакет\n"
        f"3. Выберите банк для оплаты\n"
        f"4. Переведите деньги по номеру карты\n"
        f"5. Укажите номер заказа в комментарии\n"
        f"6. Получите Stars\n\n"
        f"🔔 **После оплаты:**\n"
        f"• Stars приходят автоматически после оплаты\n"
        f"• Ожидание 1-2 минуты\n\n"
        f"🏦 **Доступные банки:**\n"
        f"{banks_list}\n\n"
        f"❓ **Проблемы с оплатой?**\n"
        f"Напишите @M1rnes"
    )
    
    await query.edit_message_text(help_text, parse_mode='Markdown')

# 🔐 АДМИН КОМАНДЫ

# Команда /admin - только для владельца
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 Все заказы", callback_data="admin_orders")],
        [InlineKeyboardButton("✅ Завершить заказ", callback_data="admin_complete")],
        [InlineKeyboardButton("🚫 Отменить заказ", callback_data="admin_cancel")],
        [InlineKeyboardButton("🔄 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Статистика
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('stars.db')
    cursor = conn.cursor()
    
    # Общая статистика
    cursor.execute('SELECT COUNT(*) FROM orders')
    total_orders = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"')
    completed_orders = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"')
    pending_orders = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "cancelled"')
    cancelled_orders = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(price) FROM orders WHERE status = "completed"')
    total_revenue = cursor.fetchone()[0] or 0
    
    # Статистика по пользователям
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM orders')
    unique_users = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 **Статистика магазина**\n\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"✅ Выполнено: {completed_orders}\n"
        f"⏳ Ожидают: {pending_orders}\n"
        f"❌ Отменено: {cancelled_orders}\n"
        f"💰 Общая выручка: {total_revenue} руб\n"
        f"👥 Уникальных пользователей: {unique_users}\n"
        f"👑 Админов: {len(ADMIN_IDS)}"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

# Просмотр всех заказов
async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('stars.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT order_number, user_name, user_username, stars, price, status, bank_selected, created_at 
        FROM orders 
        ORDER BY created_at DESC 
        LIMIT 20
    ''')
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        await query.edit_message_text("📭 Заказов пока нет")
        return
    
    orders_text = "📋 **Последние 20 заказов:**\n\n"
    
    for order in orders:
        order_number, user_name, username, stars, price, status, bank, created_at = order
        
        status_icons = {
            'completed': '✅',
            'cancelled': '❌', 
            'pending': '⏳'
        }
        
        bank_name = BANK_DETAILS.get(bank, {}).get('name', 'Не выбран')
        
        orders_text += (
            f"{status_icons.get(status, '⚪')} Заказ #{order_number}\n"
            f"👤 {user_name} (@{username if username else 'нет'})\n"
            f"⭐ {stars} Stars - {price} руб\n"
            f"🏦 {bank_name}\n"
            f"📊 {status} | {created_at[:16]}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(orders_text, reply_markup=reply_markup)

# Завершить заказ
async def admin_complete_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'complete'
    
    await query.edit_message_text(
        "✅ **Завершение заказа**\n\n"
        "Введите номер заказа для завершения:",
        parse_mode='Markdown'
    )

# Отменить заказ  
async def admin_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'cancel'
    
    await query.edit_message_text(
        "🚫 **Отмена заказа**\n\n"
        "Введите номер заказа для отмены:",
        parse_mode='Markdown'
    )

# Обработка текстовых команд админа
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    text = update.message.text.strip()
    
    # Проверяем, является ли текст номером заказа
    if text.isdigit():
        order_number = int(text)
        action = context.user_data.get('admin_action')
        
        conn = sqlite3.connect('stars.db')
        cursor = conn.cursor()
        
        # Получаем информацию о заказе
        cursor.execute('SELECT user_id, status, stars, user_name FROM orders WHERE order_number = ?', (order_number,))
        order = cursor.fetchone()
        
        if not order:
            await update.message.reply_text(f"❌ Заказ #{order_number} не найден")
            return
        
        user_id, current_status, stars, user_name = order

        if action == 'complete':
            if current_status == 'completed':
                await update.message.reply_text(f"⚠️ Заказ #{order_number} уже завершен")
                return
                
            # Обновляем статус
            cursor.execute('UPDATE orders SET status = "completed" WHERE order_number = ?', (order_number,))
            conn.commit()
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    user_id,
                    f"🎉 **Ваш заказ завершен!**\n\n"
                    f"Заказ #{order_number} на {stars} Stars выполнен!\n"
                    f"Stars должны прийти в течение 1-2 минут.\n\n"
                    f"Спасибо за покупку! ❤️"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            
            await update.message.reply_text(f"✅ Заказ #{order_number} завершен. Пользователь уведомлен.")
            
        elif action == 'cancel':
            if current_status == 'cancelled':
                await update.message.reply_text(f"⚠️ Заказ #{order_number} уже отменен")
                return
                
            # Обновляем статус
            cursor.execute('UPDATE orders SET status = "cancelled" WHERE order_number = ?', (order_number,))
            conn.commit()
            
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    user_id,
                    f"❌ **Ваш заказ отменен**\n\n"
                    f"Заказ #{order_number} отменен администратором.\n"
                    f"Если вы уже оплатили заказ, средства будут возвращены.\n\n"
                    f"По вопросам обращайтесь к @M1rnes"
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            
            await update.message.reply_text(f"🚫 Заказ #{order_number} отменен. Пользователь уведомлен.")
        
        conn.close()
        context.user_data.pop('admin_action', None)
    else:
        await update.message.reply_text("❌ Введите корректный номер заказа (только цифры)")

# Назад в админ панель
async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 Все заказы", callback_data="admin_orders")],
        [InlineKeyboardButton("✅ Завершить заказ", callback_data="admin_complete")],
        [InlineKeyboardButton("🚫 Отменить заказ", callback_data="admin_cancel")],
        [InlineKeyboardButton("🔄 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔐 **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Обработка ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

# Основная функция
def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обычные обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))  # 🔐 Новая команда!
    application.add_handler(CallbackQueryHandler(show_packages, pattern="^buy_stars$"))
    application.add_handler(CallbackQueryHandler(select_bank, pattern="^package_"))
    application.add_handler(CallbackQueryHandler(create_order, pattern="^bank_"))
    application.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    
    # 🔐 Админ обработчики
    application.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_orders, pattern="^admin_orders$"))
    application.add_handler(CallbackQueryHandler(admin_complete_order, pattern="^admin_complete$"))
    application.add_handler(CallbackQueryHandler(admin_cancel_order, pattern="^admin_cancel$"))
    application.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    
    # Обработчик текстовых команд админа
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("🤖 Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()
