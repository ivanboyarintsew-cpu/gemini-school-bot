import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Хранилище истории сообщений для каждого пользователя: {user_id: [history]}
user_histories = {}

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Сбрасываем историю при вызове /start
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("Привет! Я твой ИИ-помощник с памятью и доступом к Google Поиску. Задай мне любой вопрос!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    # Добавляем новое сообщение пользователя в историю
    user_histories[user_id].append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    # Список надежных моделей для каскада
    models = ['gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-3.7-flash']
    response_text = None

    for model_name in models:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=user_histories[user_id],
                config={
                    "tools": [{"google_search": {}}]
                }
            )
            if response and response.text:
                response_text = response.text
                break
        except Exception as e:
            continue

    if response_text:
        # Сохраняем ответ ИИ в историю, чтобы бот помнил контекст
        user_histories[user_id].append({
            "role": "model",
            "parts": [{"text": response_text}]
        })
        await update.message.reply_text(response_text)
    else:
        # При ошибке удаляем последнее сообщение пользователя, чтобы не ломать цепочку
        user_histories[user_id].pop()
        await update.message.reply_text("Не удалось получить ответ. Попробуй отправку ещё раз!")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
