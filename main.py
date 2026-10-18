import os
import asyncio
from flask import Flask, request, abort
import google.generativeai as genai
from google.generativeai.types import Tool
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests as req

TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GEMINI_API_KEY")
RENDER_URL = "https://gemini-school-bot-t983.onrender.com"

# Секретный ключ для вебхука (надежная защита от спама и поддельных запросов)
WEBHOOK_SECRET = "my_super_secret_webhook_key_12345"

genai.configure(api_key=GEMINI_KEY)

# Инструмент для веб-поиска Google через Gemini
search_tool = Tool(
    google_search_retrieval={"dynamic_threshold": 0.3}
)

# Обычная модель для учебы и общения
model_standard = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite',
    system_instruction="Ты — дружелюбный школьный ИИ-помощник. Собеседника зовут Ваня, он учится в 7 классе. Всегда помни его имя, общайся тепло, поддерживай и помогай с учебой (алгебра и другие предметы)."
)

# Модель с включенным веб-поиском для актуальных данных из интернета
model_web = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite',
    tools=[search_tool],
    system_instruction="Ты — школьный ИИ-помощник с доступом к поиску в Google. Используй актуальные данные из интернета, чтобы давать точные и свежие ответы для Вани (7 класс)."
)

# Словарь для хранения истории чатов каждого пользователя
user_chats = {}

app_flask = Flask(__name__)
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_chats[user_id] = model_standard.start_chat(history=[])
    await update.message.reply_text(
        "Привет, Ваня! Я на связи, надежно защищен и готов помогать.\n\n"
        "💡 Если нужен поиск в интернете, просто начни сообщение с команды `/websearch` или напиши слово `websearch`!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    text = update.message.text or update.message.caption or ""
    
    # Проверяем, запрашивает ли пользователь поиск в интернете
    use_web = False
    if text.startswith("/websearch") or text.lower().startswith("websearch") or "websearch" in text.lower():
        use_web = True
        # Очищаем текст от команды, чтобы модель отвечала по существу
        clean_text = text.replace("/websearch", "").replace("websearch", "").replace("WebSearch", "").strip()
        if not clean_text and update.message.photo:
            clean_text = "Найди информацию об этом в интернете"
    else:
        clean_text = text

    # Выбираем модель (с поиском или стандартную)
    active_model = model_web if use_web else model_standard

    if user_id not in user_chats:
        user_chats[user_id] = active_model.start_chat(history=[])
    
    chat = user_chats[user_id]
    response_text = None
    
    try:
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()
            caption = clean_text or "Реши это задание"
            
            image_part = {
                "mime_type": "image/jpeg",
                "data": bytes(photo_bytes)
            }
            response = chat.send_message([image_part, caption])
            if response and response.text:
                response_text = response.text.strip()
                
        elif clean_text:
            response = chat.send_message(clean_text)
            if response and response.text:
                response_text = response.text.strip()
    except Exception as e:
        print(f"GenAI Error: {e}")
        try:
            user_chats[user_id] = active_model.start_chat(history=[])
            chat = user_chats[user_id]
            if clean_text:
                response = chat.send_message(clean_text)
                if response and response.text:
                    response_text = response.text.strip()
        except Exception as inner_e:
            print(f"Inner GenAI Error: {inner_e}")

    if response_text:
        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Не удалось получить ответ. Попробуй еще раз!")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))

@app_flask.route('/')
def home():
    return "Bot is active, secured and web-search enabled!"

# Защищенный маршрут вебхука с проверкой секретного токена
@app_flask.route(f"/{WEBHOOK_SECRET}", methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        abort(403) # Блокируем любые сторонние запросы
        
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
        # Устанавливаем вебхук с передачей секретного заголовка
        webhook_url = f"{RENDER_URL}/{WEBHOOK_SECRET}"
        req.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}&secret_token={WEBHOOK_SECRET}")
    except Exception as e:
        print(f"Set webhook error: {e}")

    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)
