import os
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я ИИ-помощник. Задай мне любой вопрос по урокам!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=update.message.text,
        )
        await update.message.reply_text(response.text)
    except Exception:
        await update.message.reply_text("Произошла ошибка при ответе. Попробуй позже!")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
