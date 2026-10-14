import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я на связи и готов помочь с учебой.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contents = []
    response_text = None

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
    elif update.message.text:
        contents = update.message.text
    else:
        return

    try:
        response = ai_client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=contents
        )
        if response and response.text:
            response_text = response.text.strip()
    except Exception as e:
        print(f"GenAI Error: {e}")

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
    
    # drop_pending_updates=True сбрасывает старые зависшие запросы при перезапуске
    app.run_polling(drop_pending_updates=True)
