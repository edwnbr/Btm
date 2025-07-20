import os
import logging
import threading
import time
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# ====== CONFIG ======
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}/{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 8443))

# ====== LOGGING ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== INIT ======
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

user_data = {}

# ====== LANG TEXT ======
texts = {
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your Settings:",
        "confirm": "✅ You selected: ",
        "select_lang": "🌐 Choose your language:",
        "verified_first": "🚫 Please complete CAPTCHA first.",
        "main_menu": [["🌐 Language", "⚙️ Settings"], ["📈 Select Exchange"]],
        "select_exchange": "📊 Choose exchange to monitor:",
        "selected_exchange": "✅ Selected exchange: ",
        "price_alert": "🚨 {symbol} changed by {change:.2f}% on {exchange} in {interval} min!"
    },
    "ru": {
        "start": "👋 Привет! Пройди капчу, чтобы продолжить.",
        "captcha_passed": "✅ Верификация прошла успешно!",
        "language_selected": "🌐 Язык установлен: Русский",
        "menu": "👇 Выбери действие:",
        "settings": "⚙️ Ваши настройки:",
        "confirm": "✅ Вы выбрали: ",
        "select_lang": "🌐 Выберите язык:",
        "verified_first": "🚫 Сначала подтвердите CAPTCHA.",
        "main_menu": [["🌐 Язык", "⚙️ Настройки"], ["📈 Выбор Биржи"]],
        "select_exchange": "📊 Выберите биржу для отслеживания:",
        "selected_exchange": "✅ Выбрана биржа: ",
        "price_alert": "🚨 {symbol} изменился на {change:.2f}% на {exchange} за {interval} мин!"
    }
}

# ====== KEYBOARDS ======
def get_keyboard(lang):
    return ReplyKeyboardMarkup(texts[lang]["main_menu"], resize_keyboard=True)

# ====== COMMANDS ======
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "verified": False,
        "lang": "en",
        "exchange": "binance",
        "interval": 1,
        "threshold": 2.0
    }
    update.message.reply_text(
        texts["en"]["start"],
        reply_markup=ReplyKeyboardMarkup([["✅ I'm not a bot"]], resize_keyboard=True)
    )

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text
    lang = user_data.get(user_id, {}).get("lang", "en")

    # CAPTCHA
    if not user_data.get(user_id, {}).get("verified"):
        if message in ["✅ I'm not a bot", "✅ Я не бот"]:
            user_data[user_id]["verified"] = True
            update.message.reply_text(texts[lang]["captcha_passed"], reply_markup=get_keyboard(lang))
        else:
            update.message.reply_text(texts[lang]["verified_first"])
        return

    # Язык
    if message in ["🌐 Language", "🌐 Язык"]:
        update.message.reply_text(
            texts[lang]["select_lang"],
            reply_markup=ReplyKeyboardMarkup([["English", "Русский"]], resize_keyboard=True)
        )
    elif message == "English":
        user_data[user_id]["lang"] = "en"
        update.message.reply_text(texts["en"]["language_selected"], reply_markup=get_keyboard("en"))
    elif message == "Русский":
        user_data[user_id]["lang"] = "ru"
        update.message.reply_text(texts["ru"]["language_selected"], reply_markup=get_keyboard("ru"))

    # Настройки
    elif message in ["⚙️ Settings", "⚙️ Настройки"]:
        info = user_data.get(user_id, {})
        exch = info.get("exchange", "binance")
        interval = info.get("interval", 1)
        thresh = info.get("threshold", 2.0)
        verified = info.get("verified", False)
        response = f"{texts[lang]['settings']}\n\nExchange: {exch}\nInterval: {interval} min\nThreshold: {thresh}%\nVerified: {'Yes' if verified else 'No'}"
        update.message.reply_text(response, reply_markup=get_keyboard(lang))

    # Выбор биржи
    elif message in ["📈 Select Exchange", "📈 Выбор Биржи"]:
        update.message.reply_text(
            texts[lang]["select_exchange"],
            reply_markup=ReplyKeyboardMarkup([["Binance", "Bybit"]], resize_keyboard=True)
        )
    elif message in ["Binance", "Bybit"]:
        user_data[user_id]["exchange"] = message.lower()
        update.message.reply_text(
            texts[lang]["selected_exchange"] + message,
            reply_markup=get_keyboard(lang)
        )

    # Иное
    else:
        update.message.reply_text(texts[lang]["confirm"] + message)

# ====== PRICE MONITORING (BINANCE & BYBIT) ======
def monitor_prices():
    last_prices = {}

    while True:
        for user_id, config in user_data.items():
            if not config.get("verified"):
                continue

            exchange = config.get("exchange", "binance")
            interval = config.get("interval", 1)
            threshold = config.get("threshold", 2.0)
            lang = config.get("lang", "en")

            try:
                if exchange == "binance":
                    url = "https://api.binance.com/api/v3/ticker/price"
                    resp = requests.get(url, timeout=10)
                    data = resp.json()
                    for symbol in data:
                        pair = symbol["symbol"]
                        if not pair.endswith("USDT"): continue
                        price = float(symbol["price"])

                        prev = last_prices.get((user_id, pair))
                        if prev:
                            change = ((price - prev) / prev) * 100
                            if abs(change) >= threshold:
                                bot.send_message(user_id, texts[lang]["price_alert"].format(
                                    symbol=pair,
                                    change=change,
                                    exchange="Binance",
                                    interval=interval
                                ))
                        last_prices[(user_id, pair)] = price

                elif exchange == "bybit":
                    url = "https://api.bybit.com/v2/public/tickers"
                    resp = requests.get(url, timeout=10)
                    data = resp.json().get("result", [])
                    for symbol in data:
                        pair = symbol["symbol"]
                        if "USDT" not in pair: continue
                        price = float(symbol["last_price"])

                        prev = last_prices.get((user_id, pair))
                        if prev:
                            change = ((price - prev) / prev) * 100
                            if abs(change) >= threshold:
                                bot.send_message(user_id, texts[lang]["price_alert"].format(
                                    symbol=pair,
                                    change=change,
                                    exchange="Bybit",
                                    interval=interval
                                ))
                        last_prices[(user_id, pair)] = price

            except Exception as e:
                logger.error(f"Error monitoring {exchange}: {e}")

        time.sleep(60)

# ====== FLASK & TELEGRAM ======
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running."

# ====== MAIN ======
def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    bot.set_webhook(url=WEBHOOK_URL)

    # Start background thread
    threading.Thread(target=monitor_prices, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
