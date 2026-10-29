import os
import django
from django.conf import settings
import asyncio # Импортируем asyncio для асинхронных операций

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from cargo_14.telegram_utils import send_telegram_notification, get_site_statistics_message, get_user_info_message

# Получаем токен бота из .env
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') # Для отправки сообщений, если нужно

# --- Функции-обработчики команд ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start"""
    user = update.effective_user
    await update.message.reply_html(
        f"Assalomu alaykum, {user.mention_html()}! Men Cargo-14 botiman.\n"
        "Statistikani olish uchun /stats buyrug'ini yuboring."
    )

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет информацию о пользователе по его имени пользователя."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите имя пользователя после команды /userinfo. Пример: /userinfo username")
        return

    username = context.args[0] # Берем первое слово после команды как имя пользователя
    user_info_message = await get_user_info_message(username)
    await update.message.reply_html(user_info_message)

def main() -> None:
    """Запускает бота."""
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in .env. Please set it to run the bot.")
        return

    # Отправляем приветственное сообщение при запуске бота
    # Это будет отправлено в чат, указанный в TELEGRAM_CHAT_ID
    initial_message = "🚀 Django Cargo-14 bot muvaffaqiyatli ishga tushdi!\nStatistika va xabarnomalar faol."
    send_telegram_notification(initial_message) # Используем send_telegram_notification

    # Создаем объект Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("userinfo", user_info_command))

    # Запускаем бота
    print("Bot is starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()