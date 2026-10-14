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
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой ИИ-помощник. Задай мне любой вопрос!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Список моделей для проверки
    models = ['gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-3.7-flash']
    
    last_error = ""

    for model_name in models:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=user_message,
            )
            if response and response.text:
                await update.message.reply_text(response.text)
                return
        except Exception as e:
            last_error = str(e)
            continue

    # Если ни одна модель не ответила, покажем ошибку для диагностики
    await update.message.reply_text(f"Не удалось ответить. Ошибка API: {last_error}")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
