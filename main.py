import os
import asyncio
from flask import Flask, request, abort
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests as req

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")
RENDER_URL = "https://gemini-school-bot-t983.onrender.com"

WEBHOOK_SECRET = "my_super_secret_webhook_key_12345"

genai.configure(api_key=GEMINI_KEY)

# Создаем базовую модель с возможностью поиска
model_standard = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite',
    system_instruction="Ты — Сэм, дружелюбный ИИ-помощник. Собеседника зовут Ваня (7 класс). Общайся тепло, помогай с учебой."
)

model_web = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite',
    tools=["google_search_retrieval"],
    system_instruction="Ты — Сэм, ИИ-помощник с доступом к Google Поиску. Давай Ване самые актуальные данные из интернета."
)

# Храним чаты и выбранный режим пользователей
user_chats = {}
user_modes = {} # 'standard' или 'web'

app_flask = Flask(__name__)
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_modes[user_id] = 'standard'
    user_chats[user_id] = model_standard.start_chat(history=[])
    
    await update.message.reply_text(
        "Привет, Ваня! Я Сэм — твой ИИ-помощник.\n\n"
        "💬 Сейчас включен **Обычный режим** (для учебы и общения).\n"
        "🌐 Чтобы искать свежую информацию в интернете, напиши `/websearch` или просто отправь ключевое слово `websearch`.\n"
        "🔄 Чтобы вернуться в обычный режим, напиши `/standard`."
    )

async def set_web_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_modes[user_id] = 'web'
    user_chats[user_id] = model_web.start_chat(history=[])
    await update.message.reply_text("🌐 **Режим веб-поиска Google включен!** Задавай любой вопрос, я найду ответы в интернете.")

async def set_standard_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_modes[user_id] = 'standard'
    user_chats[user_id] = model_standard.start_chat(history=[])
    await update.message.reply_text("💬 **Обычный режим включен!** Помогаю с учебой и вопросами.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or update.message.caption or ""
    
    # Автопереключение по ключевым словам в тексте
    if text.lower().startswith("websearch") or text.lower().startswith("/websearch"):
        user_modes[user_id] = 'web'
        user_chats[user_id] = model_web.start_chat(history=[])
        text = text.replace("/websearch", "").replace("websearch", "").replace("WebSearch", "").strip()
        if not text:
            await update.message.reply_text("🌐 Включен режим веб-поиска! Напиши свой вопрос.")
            return

    # Если пользователь еще не начинал чат
    current_mode = user_modes.get(user_id, 'standard')
    if user_id not in user_chats:
        active_model = model_web if current_mode == 'web' else model_standard
        user_chats[user_id] = active_model.start_chat(history=[])
        
    chat = user_chats[user_id]
    response_text = None
    
    try:
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            caption = text or "Реши это задание"
            image_part = {"mime_type": "image/jpeg", "data": bytes(photo_bytes)}
            response = chat.send_message([image_part, caption])
            if response and response.text:
                response_text = response.text.strip()
                
        elif text:
            response = chat.send_message(text)
            if response and response.text:
                response_text = response.text.strip()
    except Exception as e:
        print(f"GenAI Error: {e}")
        # При ошибке сбрасываем и пересоздаем сессию
        active_model = model_web if current_mode == 'web' else model_standard
        user_chats[user_id] = active_model.start_chat(history=[])
        chat = user_chats[user_id]
        if text:
            try:
                response = chat.send_message(text)
                if response and response.text:
                    response_text = response.text.strip()
            except Exception as inner_e:
                print(f"Inner Error: {inner_e}")

    if response_text:
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Не удалось получить ответ. Попробуй еще раз!")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("websearch", set_web_mode))
telegram_app.add_handler(CommandHandler("standard", set_standard_mode))
telegram_app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

@app_flask.route('/')
def home():
    return "Bot is active and running!"

@app_flask.route(f"/{WEBHOOK_SECRET}", methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        abort(403)
        
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
    try:
        webhook_url = f"{RENDER_URL}/{WEBHOOK_SECRET}"
        req.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}&secret_token={WEBHOOK_SECRET}")
    except Exception as e:
        print(f"Set webhook error: {e}")

    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)
