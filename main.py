import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Хранилище истории сообщений для каждого пользователя
user_history = {}

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
    response_text = None

    # Обработка фотографий
    if update.message.photo:
        try:
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
        except Exception:
            pass

    # Обработка текстовых сообщений с историей
    elif update.message.text:
        user_message = update.message.text
        
        # Собираем короткий контекст последних сообщений (до 4 штук)
        history_snippet = "\n".join(user_history[user_id][-4:])
        contents = f"{history_snippet}\nПользователь: {user_message}\nАссистент:"
        
        user_history[user_id].append(f"Пользователь: {user_message}")
    else:
        return

    # Каскад стабильных моделей
    models = ['gemini-2.5-flash', 'gemini-3.1-flash-lite', 'gemini-3.7-flash']

    for model_name in models:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=contents
            )
            if response and response.text:
                response_text = response.text.strip()
                break
        except Exception:
            continue

    if response_text:
        if update.message.text:
            user_history[user_id].append(f"Ассистент: {response_text}")
            # Ограничиваем длину истории, чтобы не перегружать запрос
            if len(user_history[user_id]) > 10:
                user_history[user_id] = user_history[user_id][-10:]
                
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Не удалось распознать или получить ответ. Попробуй еще раз!")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
