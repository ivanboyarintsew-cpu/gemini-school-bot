import os
import asyncio
from flask import Flask, request
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests as req

TELEGRAM_TOKEN = "8873295583:AAFkxlPOzOtkjbBuHAQFEVSlL37YB8cBWO8"
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")
RENDER_URL = "https://gemini-school-bot-t983.onrender.com"

ai_client = genai.Client(api_key=GEMINI_KEY)

app_flask = Flask(__name__)

# Инициализируем Telegram приложение для вебхуков
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Бот успешно переведен на Webhook и готов помогать с учебой без сбоев.")

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

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

@app_flask.route('/')
def home():
    return "Bot is active and running via Webhook!"

@app_flask.route(f"/{TELEGRAM_TOKEN}", methods=['POST'])
def webhook():
    """Принимаем сообщения от Telegram через вебхук."""
    json_data = request.get_json(force=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def process():
        await telegram_app.initialize()
        update = Update.de_json(json_data, telegram_app.bot)
        await telegram_app.process_update(update)
    loop.run_until_complete(process())
    return "OK", 200

if __name__ == '__main__':
    # Автоматически регистрируем вебхук в Telegram при старте сервера
    try:
        req.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}/{TELEGRAM_TOKEN}")
    except Exception as e:
        print(f"Set webhook error: {e}")

    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)
