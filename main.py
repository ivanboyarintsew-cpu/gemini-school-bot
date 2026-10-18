import os
import asyncio
from flask import Flask, request, abort
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests as req

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")
RENDER_URL = "https://gemini-school-bot-t983.onrender.com"

# Секретный ключ вебхука для защиты от сторонних запросов
WEBHOOK_SECRET = "my_super_secret_webhook_key_12345"

genai.configure(api_key=GEMINI_KEY)

# Единая надежная модель
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite',
    system_instruction=(
        "Ты — Сэм, дружелюбный ИИ-помощник. Собеседника зовут Ваня, он учится в 7 классе. "
        "Общайся тепло, поддерживай, помогай с учебой (алгебра и другие предметы). "
        "Ты обладаешь широкими знаниями об актуальных событиях, киберспорте (CS2, Team Spirit), погоде и мире. "
        "Если пользователь запрашивает поиск или свежие факты, давай самые точные и свежие данные."
    )
)

# Храним историю чатов пользователей
user_chats = {}

app_flask = Flask(__name__)
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_chats[user_id] = model.start_chat(history=[])
    
    await update.message.reply_text(
        "Привет, Ваня! Я Сэм — твой ИИ-помощник. Я на связи и надежно защищен! 🛡️\n\n"
        "💬 Помогаю с учебой, задачами и отвечу на любой вопрос по интернету (погода, новости, киберспорт)."
    )

async def set_web_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
    await update.message.reply_text("🌐 **Режим поиска включен!** Напиши свой вопрос о погоде, новостях или фактах.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or update.message.caption or ""
    
    # Очищаем возможные префиксы команд
    if text.lower().startswith("websearch") or text.lower().startswith("/websearch"):
        text = text.replace("/websearch", "").replace("websearch", "").replace("WebSearch", "").strip()
        if not text:
            await update.message.reply_text("🌐 Задавай любой вопрос, я найду ответ!")
            return

    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
        
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
        # Если возник сбой, перезапускаем сессию чата без потери бота
        try:
            user_chats[user_id] = model.start_chat(history=[])
            chat = user_chats[user_id]
            if text:
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
telegram_app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

@app_flask.route('/')
def home():
    return "Bot is active, secured and fully working!"

# Защищенный вебхук с проверкой X-Telegram-Bot-Api-Secret-Token
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
