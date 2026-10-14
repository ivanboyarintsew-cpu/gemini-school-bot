import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Словарь для хранения истории чатов каждого пользователя: {user_id: chat_session}
user_chats = {}

# Веб-сервер для поддержания активности на Render
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Сбрасываем историю при команде /start
    if user_id in user_chats:
        del user_chats[user_id]
    await update.message.reply_text("Привет! Я быстрый ИИ-помощник с доступом к интернету и памятью. Задай мне любой вопрос!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    try:
        # Если у этого пользователя еще нет активной сессии чата, создаем её
        if user_id not in user_chats:
            user_chats[user_id] = ai_client.chats.create(model="gemini-3.1-flash-lite")
        
        chat_session = user_chats[user_id]

        # Отправляем сообщение в рамках истории сессии с поддержкой поиска в Google
        response = chat_session.send_message(
            user_message,
            config={
                "tools": [{"google_search": {}}]
            }
        )
        
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
