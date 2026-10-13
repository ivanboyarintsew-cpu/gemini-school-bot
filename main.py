import os
import time
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Веб-сервер для поддержания активности на Render
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я ИИ-помощник. Задай мне любой вопрос по урокам!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Делаем до 3 попыток обращения к Gemini 3.8 Flash при перегрузках
    for attempt in range(3):
        try:
            response = ai_client.models.generate_content(
                model='gemini-3.8-flash',
                contents=update.message.text,
            )
            await update.message.reply_text(response.text)
            return
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                time.sleep(2)  # Ждем 2 секунды и пробуем снова
                continue
            else:
                await update.message.reply_text(f"Ошибка: {e}")
                return

    # Если после 3 попыток сервер всё еще перегружен
    await update.message.reply_text("Сервер Gemini сейчас сильно перегружен. Попробуй отправить сообщение еще раз через пару минут!")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
