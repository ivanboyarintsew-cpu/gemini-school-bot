import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Хранилище сессий чата для каждого пользователя
user_chats = {}

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    await update.message.reply_text("Привет! Я быстрый ИИ-помощник с памятью и доступом к Google Поиску. Спроси меня о чём угодно!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Каскад актуальных моделей 3-го поколения
    models_cascade = ['gemini-3.1-flash-lite', 'gemini-3.6-flash', 'gemini-3.5-flash-lite']

    for model_name in models_cascade:
        try:
            if user_id not in user_chats:
                user_chats[user_id] = ai_client.chats.create(model=model_name)
            
            chat_session = user_chats[user_id]

            response = chat_session.send_message(
                user_message,
                config={
                    "tools": [{"google_search": {}}]
                }
            )
            await update.message.reply_text(response.text)
            return  
            
        except Exception as e:
            error_str = str(e)
            if any(err in error_str for err in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "NOT_FOUND"]):
                if user_id in user_chats:
                    del user_chats[user_id]
                continue
            else:
                await update.message.reply_text(f"Ошибка: {e}")
                return

    await update.message.reply_text("Все бесплатные лимиты моделей на сегодня исчерпаны. Попробуй позже!")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
