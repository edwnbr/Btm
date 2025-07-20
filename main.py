import os
import logging
import requests
import threading
import time
from flask import Flask, request
from telegram import (
    Bot, Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
)

# ===================== CONFIG =====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 8443))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "select_language": "Выберите язык:",
        "select_exchange": "Выберите биржу:",
        "select_market": "Выберите тип рынка:",
        "select_timeframe": "Выберите таймфрейм:",
        "select_threshold": "Выберите % изменения:",
        "spot": "Спот",
        "futures": "Фьючерсы",
        "back": "⬅️ Назад",
        "main_menu": [
            ["🌐 Язык", "⚙️ Настройки"],
            ["📊 Биржа", "💱 Рынок"],
            ["⏱️ Таймфрейм", "📈 Порог %"]
        ],
        "available_exchanges": ["Binance", "Bybit", "MEXC", "BingX"],
        "verified": "Да" ,
        "not_verified": "Нет"
    },
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your Settings:",
        "confirm": "✅ You selected: ",
        "select_language": "Choose a language:",
        "select_exchange": "Choose exchange:",
        "select_market": "Choose market type:",
        "select_timeframe": "Choose timeframe:",
        "select_threshold": "Choose % change threshold:",
        "spot": "Spot",
        "futures": "Futures",
        "back": "⬅️ Back",
        "main_menu": [
            ["🌐 Language", "⚙️ Settings"],
            ["📊 Exchange", "💱 Market"],
            ["⏱️ Timeframe", "📈 Threshold %"]
        ],
        "available_exchanges": ["Binance", "Bybit", "MEXC", "BingX"],
        "verified": "Yes",
        "not_verified": "No"
    }
}

def get_lang(user_id):
    return user_data.get(user_id, {}).get("lang", "en")

def get_keyboard(user_id):
    lang = get_lang(user_id)
    return ReplyKeyboardMarkup(
        texts[lang]["main_menu"],
        resize_keyboard=True
    )

# ===================== COMMANDS =====================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "verified": False,
        "lang": "en",
        "exchange": "Binance",
        "market": "spot",
        "timeframe": "1m",
        "threshold": 1.0
    }
    lang = get_lang(user_id)
    update.message.reply_text(
        texts[lang]["start"],
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("✅ I'm not a bot")]],
            resize_keyboard=True
        )
    )

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    msg = update.message.text
    lang = get_lang(user_id)

    if not user_data.get(user_id, {}).get("verified", False):
        if msg in ["✅ I'm not a bot", "✅ Я не бот"]:
            user_data[user_id]["verified"] = True
            update.message.reply_text(
                texts[lang]["captcha_passed"],
                reply_markup=get_keyboard(user_id)
            )
        else:
            update.message.reply_text(
                "🚫 Please verify first." if lang == "en" else "🚫 Сначала пройдите верификацию."
            )
        return

    # Language
    if msg in ["🌐 Language", "🌐 Язык"]:
        update.message.reply_text(
            texts[lang]["select_language"],
            reply_markup=ReplyKeyboardMarkup(
                [["English", "Русский"], [texts[lang]["back"]]],
                resize_keyboard=True
            )
        )
    elif msg in ["English", "Русский"]:
        user_data[user_id]["lang"] = "en" if msg == "English" else "ru"
        lang = get_lang(user_id)
        update.message.reply_text(
            texts[lang]["language_selected"],
            reply_markup=get_keyboard(user_id)
        )

    # Settings
    elif msg in ["⚙️ Settings", "⚙️ Настройки"]:
        data = user_data[user_id]
        text = f"""{texts[lang]["settings"]}

🌐 Language: {data['lang'].upper()}
📊 Exchange: {data['exchange']}
💱 Market: {texts[lang]["spot"] if data['market'] == "spot" else texts[lang]["futures"]}
⏱️ Timeframe: {data['timeframe']}
📈 Threshold: {data['threshold']}%
✅ Verified: {texts[lang]["verified"] if data['verified'] else texts[lang]["not_verified"]}
"""
        update.message.reply_text(text, reply_markup=get_keyboard(user_id))

    # Exchange
    elif msg in ["📊 Exchange", "📊 Биржа"]:
        update.message.reply_text(
            texts[lang]["select_exchange"],
            reply_markup=ReplyKeyboardMarkup(
                [texts[lang]["available_exchanges"], [texts[lang]["back"]]],
                resize_keyboard=True
            )
        )
    elif msg in texts[lang]["available_exchanges"]:
        user_data[user_id]["exchange"] = msg
        update.message.reply_text(
            texts[lang]["confirm"] + msg,
            reply_markup=get_keyboard(user_id)
        )

    # Market
    elif msg in ["💱 Market", "💱 Рынок"]:
        update.message.reply_text(
            texts[lang]["select_market"],
            reply_markup=ReplyKeyboardMarkup(
                [[texts[lang]["spot"], texts[lang]["futures"]], [texts[lang]["back"]]],
                resize_keyboard=True
            )
        )
    elif msg in [texts[lang]["spot"], texts[lang]["futures"]]:
        user_data[user_id]["market"] = "spot" if msg == texts[lang]["spot"] else "futures"
        update.message.reply_text(
            texts[lang]["confirm"] + msg,
            reply_markup=get_keyboard(user_id)
        )

    # Timeframe
    elif msg in ["⏱️ Timeframe", "⏱️ Таймфрейм"]:
        update.message.reply_text(
            texts[lang]["select_timeframe"],
            reply_markup=ReplyKeyboardMarkup(
                [["1m", "5m", "15m", "1h"], [texts[lang]["back"]]],
                resize_keyboard=True
            )
        )
    elif msg in ["1m", "5m", "15m", "1h"]:
        user_data[user_id]["timeframe"] = msg
        update.message.reply_text(
            texts[lang]["confirm"] + msg,
            reply_markup=get_keyboard(user_id)
        )

    # Threshold
    elif msg in ["📈 Threshold %", "📈 Порог %"]:
        update.message.reply_text(
            texts[lang]["select_threshold"],
            reply_markup=ReplyKeyboardMarkup(
                [["0.5", "1.0", "2.0", "5.0"], [texts[lang]["back"]]],
                resize_keyboard=True
            )
        )
    elif msg in ["0.5", "1.0", "2.0", "5.0"]:
        user_data[user_id]["threshold"] = float(msg)
        update.message.reply_text(
            texts[lang]["confirm"] + msg + "%",
            reply_markup=get_keyboard(user_id)
        )

    elif msg == texts[lang]["back"]:
        update.message.reply_text(
            texts[lang]["menu"],
            reply_markup=get_keyboard(user_id)
        )
    else:
        update.message.reply_text(
            texts[lang]["confirm"] + msg,
            reply_markup=get_keyboard(user_id)
        )

# ===================== MONITORING DEMO =====================
def monitor_prices():
    prev_prices = {}
    while True:
        time.sleep(30)
        for user_id, data in user_data.items():
            if not data.get("verified"): continue
            if data["exchange"] != "Binance": continue  # Только Binance demo

            try:
                res = requests.get("https://api.binance.com/api/v3/ticker/price")
                prices = res.json()

                timeframe = data.get("timeframe", "1m")
                threshold = data.get("threshold", 1.0)
                lang = get_lang(user_id)

                if not isinstance(prices, list):
                    continue

                for item in prices:
                    symbol = item["symbol"]
                    price = float(item["price"])
                    prev_price = prev_prices.get(symbol)

                    if prev_price:
                        change = ((price - prev_price) / prev_price) * 100
                        if abs(change) >= threshold:
                            bot.send_message(
                                chat_id=user_id,
                                text=f"🚨 {symbol} изменился на {change:.2f}%"
                            )
                    prev_prices[symbol] = price
            except Exception as e:
                logger.error(f"Monitor error: {e}")

threading.Thread(target=monitor_prices, daemon=True).start()

# ===================== FLASK =====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def home():
    return "Bot running."

def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
