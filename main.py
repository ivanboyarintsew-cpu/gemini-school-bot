import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой ИИ-помощник. Напиши мне или отправь фото с заданием!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contents = []
    response_text = None

    # Обработка фото
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
        except Exception as e:
            print(f"Photo error: {e}")

    # Обработка текста
    elif update.message.text:
        contents = update.message.text
    else:
        return

    # Запрос к моделям Gemini
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
        except Exception as e:
            print(f"Model {model_name} error: {e}")
            continue

    if response_text:
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Не удалось получить ответ. Попробуй еще раз!")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
