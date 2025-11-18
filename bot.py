import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from collections import defaultdict

# Получаем токены из переменных окружения (безопасно!)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

# Хранилище истории диалогов (user_id -> список сообщений)
chat_history = defaultdict(list)

# Системная инструкция для бота
SYSTEM_PROMPT = """Тебя зовут Ильнур, ты татар, любишь World of Warcraft и Майнкрафт, шаришь за эчпочмаки, родом с Казахстана, щас в Москве, разговариваешь на ты."""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    # Очищаем историю при старте
    chat_history[user_id] = []
    
    await update.message.reply_text(
        'Здарова, Эчпочмак! Я Ильнур. Спрашивай чё хочешь, отвечу по делу'
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /clear - очистка истории"""
    user_id = update.effective_user.id
    chat_history[user_id] = []
    await update.message.reply_text('Окей, забыл всё что было. Начинаем с чистого листа ✅')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        '❓ Команды:\n\n'
        '• Просто пиши - я отвечу\n'
        '• /start - начать заново\n'
        '• /clear - очистить память диалога\n'
        '• /help - эта справка\n\n'
        'Помню последние 2 твоих сообщения 🧠'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Показываем, что бот печатает
    await update.message.chat.send_action(action="typing")
    
    try:
        # Добавляем сообщение пользователя в историю
        chat_history[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        # Оставляем только последние 4 сообщения (2 пары: user + assistant)
        if len(chat_history[user_id]) > 4:
            chat_history[user_id] = chat_history[user_id][-4:]
        
        # Формируем сообщения для API
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(chat_history[user_id])
        
        # Отправляем запрос к ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,  # Ограничение для краткости
            temperature=0.8
        )
        
        # Получаем ответ
        bot_reply = response['choices'][0]['message']['content']
        
        # Добавляем ответ бота в историю
        chat_history[user_id].append({
            "role": "assistant",
            "content": bot_reply
        })
        
        # Отправляем ответ пользователю
        await update.message.reply_text(bot_reply)
        
    except openai.error.RateLimitError:
        await update.message.reply_text(
            '⏳ Погоди, слишком много запросов. Попробуй через минуту.'
        )
    except openai.error.InvalidRequestError as e:
        await update.message.reply_text(
            f'❌ Чёт не то: {str(e)}'
        )
    except Exception as e:
        await update.message.reply_text(
            f'❌ Ошибочка вышла: {str(e)}\n\nПопробуй позже.'
        )
        print(f"Ошибка: {e}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f'Update {update} caused error {context.error}')


def main():
    """Главная функция запуска бота"""
    
    # Проверяем наличие токенов
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        print("❌ ОШИБКА: Не найдены переменные окружения!")
        print("Убедитесь, что установлены TELEGRAM_TOKEN и OPENAI_API_KEY")
        return
    
    print("🚀 Запуск бота Ильнура...")
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Запускаем бота
    print("✅ Бот успешно запущен!")
    print("Нажмите Ctrl+C для остановки")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
