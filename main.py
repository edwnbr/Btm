# ===================== main.py =====================
import logging
import os
import threading
import time
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, Dispatcher
)

# ========== CONFIG ==========
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 8443))

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== APP ==========
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# ========== USER DATA ==========
user_data = {}

# ========== TRANSLATIONS ==========
texts = {
    "ru": {
        "start": "👋 Привет! Пройди капчу, чтобы продолжить.",
        "captcha_passed": "✅ Верификация прошла успешно!",
        "language_selected": "🌐 Язык установлен: Русский",
        "menu": "👇 Выбери действие:",
        "settings": "⚙️ Ваши настройки:",
        "confirm": "✅ Вы выбрали: ",
        "select_exchange": "📊 Выберите биржу:",
        "select_market": "📈 Выберите рынок:",
        "select_threshold": "📉 Выберите порог (%):",
        "select_timeframe": "⏱ Выберите таймфрейм:",
        "current_settings": "⚙️ Текущие настройки:",
        "spot": "Спот",
        "futures": "Фьючерсы",
        "dump": "Дамп",
        "pump": "Памп",
        "both": "Оба",
        "main_menu": [["🌐 Язык", "⚙️ Настройки"], ["📊 Биржа", "📈 Рынок"], ["📉 Порог", "⏱ Таймфрейм"]],
        "back": "⬅️ Назад в меню",
    },
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your Settings:",
        "confirm": "✅ You selected: ",
        "select_exchange": "📊 Choose exchange:",
        "select_market": "📈 Choose market:",
        "select_threshold": "📉 Choose threshold (%):",
        "select_timeframe": "⏱ Choose timeframe:",
        "current_settings": "⚙️ Current settings:",
        "spot": "Spot",
        "futures": "Futures",
        "dump": "Dump",
        "pump": "Pump",
        "both": "Both",
        "main_menu": [["🌐 Language", "⚙️ Settings"], ["📊 Exchange", "📈 Market"], ["📉 Threshold", "⏱ Timeframe"]],
        "back": "⬅️ Back to menu",
    }
}

EXCHANGES = ["Binance", "Bybit", "MEXC", "BingX"]
MARKETS = ["spot", "futures"]
THRESHOLDS = ["1%", "3%", "5%", "10%"]
TIMEFRAMES = ["1m", "5m", "15m"]

# ========== KEYBOARD ==========
def get_keyboard(lang):
    return ReplyKeyboardMarkup(
        texts[lang]["main_menu"],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def confirm_keyboard(options, lang):
    return ReplyKeyboardMarkup(
        [[opt] for opt in options] + [[texts[lang]["back"]]],
        resize_keyboard=True
    )

# ========== HANDLERS ==========
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "verified": False,
        "lang": "en",
        "exchange": "Binance",
        "market": "spot",
        "threshold": "3%",
        "timeframe": "1m"
    }

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texts["en"]["start"],
        reply_markup=ReplyKeyboardMarkup([["✅ I'm not a bot"]], resize_keyboard=True)
    )

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    lang = user_data.get(user_id, {}).get("lang", "en")

    # CAPTCHA
    if not user_data.get(user_id, {}).get("verified"):
        if text in ["✅ I'm not a bot", "✅ Я не бот"]:
            user_data[user_id]["verified"] = True
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=texts[lang]["captcha_passed"],
                                     reply_markup=get_keyboard(lang))
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="🚫 Please verify first." if lang == "en" else "🚫 Сначала пройдите верификацию.")
        return

    # Язык
    if text in ["🌐 Language", "🌐 Язык"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Choose language / Выберите язык:",
                                 reply_markup=ReplyKeyboardMarkup([["English", "Русский"]], resize_keyboard=True))
    elif text in ["English", "Русский"]:
        user_data[user_id]["lang"] = "en" if text == "English" else "ru"
        lang = user_data[user_id]["lang"]
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["language_selected"],
                                 reply_markup=get_keyboard(lang))

    # Настройки
    elif text in ["⚙️ Settings", "⚙️ Настройки"]:
        u = user_data[user_id]
        settings_text = f"""{texts[lang]["current_settings"]}
📊 Exchange: {u['exchange']}
📈 Market: {texts[lang][u['market']]}
📉 Threshold: {u['threshold']}
⏱ Timeframe: {u['timeframe']}"""
        context.bot.send_message(chat_id=update.effective_chat.id, text=settings_text)

    # Биржа
    elif text in ["📊 Exchange", "📊 Биржа"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["select_exchange"],
                                 reply_markup=confirm_keyboard(EXCHANGES, lang))
    elif text in EXCHANGES:
        user_data[user_id]["exchange"] = text
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["confirm"] + text,
                                 reply_markup=get_keyboard(lang))

    # Рынок
    elif text in ["📈 Market", "📈 Рынок"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["select_market"],
                                 reply_markup=confirm_keyboard([texts[lang]["spot"], texts[lang]["futures"]], lang))
    elif text in [texts[lang]["spot"], texts[lang]["futures"]]:
        user_data[user_id]["market"] = "spot" if text == texts[lang]["spot"] else "futures"
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["confirm"] + text,
                                 reply_markup=get_keyboard(lang))

    # Порог
    elif text in ["📉 Threshold", "📉 Порог"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["select_threshold"],
                                 reply_markup=confirm_keyboard(THRESHOLDS, lang))
    elif text in THRESHOLDS:
        user_data[user_id]["threshold"] = text
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["confirm"] + text,
                                 reply_markup=get_keyboard(lang))

    # Таймфрейм
    elif text in ["⏱ Timeframe", "⏱ Таймфрейм"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["select_timeframe"],
                                 reply_markup=confirm_keyboard(TIMEFRAMES, lang))
    elif text in TIMEFRAMES:
        user_data[user_id]["timeframe"] = text
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["confirm"] + text,
                                 reply_markup=get_keyboard(lang))

    elif text == texts[lang]["back"]:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["menu"],
                                 reply_markup=get_keyboard(lang))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=texts[lang]["confirm"] + text,
                                 reply_markup=get_keyboard(lang))

# ========== PRICE MONITOR ==========
def price_monitor():
    while True:
        for user_id, data in user_data.items():
            if not data.get("verified"):
                continue

            exchange = data["exchange"]
            market = data["market"]
            timeframe = data["timeframe"]
            threshold = float(data["threshold"].replace("%", ""))

            # Placeholder: Replace with real API data
            price_change = 5.0  # ← simulate

            if price_change >= threshold:
                lang = data["lang"]
                msg = f"🚀 {exchange} {market.upper()} detected pump: +{price_change}%"
                bot.send_message(chat_id=user_id, text=msg)
        time.sleep(60)

threading.Thread(target=price_monitor, daemon=True).start()

# ========== FLASK ROUTES ==========
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running."

# ========== MAIN ==========
def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
