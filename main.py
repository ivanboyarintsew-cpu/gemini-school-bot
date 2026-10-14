import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Хранилище истории диалогов: {user_id: "текст переписки"}
user_sessions = {}

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("Привет! Я твой ИИ-помощник с памятью. Задай мне любой вопрос!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = ""

    # Формируем накопленный контекст диалога
    prompt = user_sessions[user_id] + f"\nПользователь: {user_message}\nАссистент:"

    models = ['gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-3.7-flash']
    response_text = None

    for model_name in models:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                response_text = response.text.strip()
                break
        except Exception as e:
            continue

    if response_text:
        # Сохраняем историю
        user_sessions[user_id] = prompt + " " + response_text
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Не удалось получить ответ. Попробуй отправить сообщение ещё раз!")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)
