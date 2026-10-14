import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

# Хранилище сессий чата для пользователей
user_chats = {}

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

def get_or_create_chat(user_id: int):
    """Создает или возвращает существующий чат с памятью."""
    if user_id not in user_chats:
        user_chats[user_id] = ai_client.chats.create(model='gemini-2.5-flash')
    return user_chats[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    await update.message.reply_text("Привет! Я твой ИИ-помощник с памятью диалога и поддержкой фото. Напиши вопрос или отправь задание!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    response_text = None

    # Если отправлено фото
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
            
            # Для фото используем прямое генеративное обращение
            models = ['gemini-2.5-flash', 'gemini-3.1-flash-lite']
            for model_name in models:
                try:
                    res = ai_client.models.generate_content(
                        model=model_name,
                        contents=contents
                    )
                    if res and res.text:
                        response_text = res.text.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass

    # Если отправлен обычный текст
    elif update.message.text:
        user_text = update.message.text
        
        # Пробуем через официальный чат-контекст с памятью
        try:
            chat = get_or_create_chat(user_id)
            res = chat.send_message(user_text)
            if res and res.text:
                response_text = res.text.strip()
        except Exception:
            # Если чат-сессия сбойнула, пересоздаем ее и пробуем еще раз
            try:
                user_chats[user_id] = ai_client.chats.create(model='gemini-2.5-flash')
                res = user_chats[user_id].send_message(user_text)
                if res and res.text:
                    response_text = res.text.strip()
            except Exception:
                pass

    if response_text:
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
