import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Хранилище текстовой истории для каждого пользователя
user_history = {}

# Создаем Flask-приложение, чтобы Render видел веб-сервис
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_history:
        del user_history[user_id]
    await update.message.reply_text("Привет! Я твой ИИ-помощник с памятью и поддержкой фото. Напиши мне или отправь задание!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_history:
        user_history[user_id] = []

    contents = []

    # Проверяем, прислал ли пользователь фото
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        caption = update.message.caption or "Реши это задание"
        
        contents = [
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": bytes(photo_bytes)
                }
            },
            caption
        ]
    elif update.message.text:
        user_message = update.message.text
        history_text = "\n".join(user_history[user_id][-6:])
        contents = f"{history_text}\nПользователь: {user_message}\nАссистент:"
        
        user_history[user_id].append(f"Пользователь: {user_message}")
    else:
        return

    models = ['gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-3.7-flash']
    response_text = None

    for model_name in models:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=contents
            )
            if response and response.text:
                response_text = response.text.strip()
                break
        except Exception as e:
            continue

    if response_text:
        if update.message.text:
            user_history[user_id].append(f"Ассистент: {response_text}")
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Не удалось распознать или получить ответ. Попробуй еще раз!")

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке, чтобы он держал веб-сервер открытым
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запуск Telegram-бота
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
