import logging
import os
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, Dispatcher
)

# ===================== CONFIG =====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"

WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 8443))

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== APP =====================
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# ===================== USER DATA =====================
user_data = {}

# ===================== TRANSLATIONS =====================
texts = {
    "ru": {
        "start": "👋 Привет! Пройди капчу, чтобы продолжить.",
        "captcha_passed": "✅ Верификация прошла успешно!",
        "language_selected": "🌐 Язык установлен: Русский",
        "menu": "👇 Выбери действие:",
        "settings": "⚙️ Ваши настройки:",
        "confirm": "✅ Вы выбрали: ",
        "main_menu": [["🌐 Язык", "⚙️ Настройки"]],
    },
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your Settings:",
        "confirm": "✅ You selected: ",
        "main_menu": [["🌐 Language", "⚙️ Settings"]],
    }
}

# ===================== KEYBOARDS =====================
def get_keyboard(lang):
    return ReplyKeyboardMarkup(
        keyboard=texts[lang]["main_menu"],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ===================== HANDLERS =====================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {"verified": False, "lang": "en"}

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texts["en"]["start"],
        reply_markup=ReplyKeyboardMarkup([["✅ I'm not a bot"]], resize_keyboard=True)
    )

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text

    # Проверка CAPTCHA
    if not user_data.get(user_id, {}).get("verified"):
        if message == "✅ I'm not a bot" or message == "✅ Я не бот":
            user_data[user_id]["verified"] = True
            lang = user_data[user_id]["lang"]
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=texts[lang]["captcha_passed"],
                reply_markup=get_keyboard(lang)
            )
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🚫 Сначала подтвердите CAPTCHA." if user_data[user_id]["lang"] == "ru" else "🚫 Please complete CAPTCHA first."
            )
        return

    lang = user_data[user_id]["lang"]

    # Выбор языка
    if message in ["🌐 Язык", "🌐 Language"]:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Выберите язык / Choose language:",
            reply_markup=ReplyKeyboardMarkup(
                [["Русский", "English"]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
    elif message == "Русский":
        user_data[user_id]["lang"] = "ru"
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts["ru"]["language_selected"],
            reply_markup=get_keyboard("ru")
        )
    elif message == "English":
        user_data[user_id]["lang"] = "en"
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts["en"]["language_selected"],
            reply_markup=get_keyboard("en")
        )
    elif message in ["⚙️ Настройки", "⚙️ Settings"]:
        current = user_data.get(user_id, {})
        settings_text = f"{texts[lang]['settings']}\n\n🌐 Язык / Language: {lang.upper()}\n✅ Верифицирован: {'Да' if current.get('verified') else 'Нет'}"
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=settings_text,
            reply_markup=get_keyboard(lang)
        )
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts[lang]["confirm"] + message,
            reply_markup=get_keyboard(lang)
        )

# ===================== FLASK WEBHOOK =====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running."

# ===================== MAIN =====================
def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
