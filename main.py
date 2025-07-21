# main.py
import logging
import os
import threading
import time
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, Dispatcher
)
import requests

# === CONFIG ===
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 8443))

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === APP ===
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# === USER DATA ===
user_data = {}

# === TEXTS ===
texts = {
    "ru": {
        "start": "👋 Привет! Пройди капчу, чтобы продолжить.",
        "captcha_passed": "✅ Верификация прошла успешно!",
        "language_selected": "🌐 Язык установлен: Русский",
        "menu": "👇 Выбери действие:",
        "settings": "⚙️ Текущие настройки:",
        "confirm": "✅ Вы выбрали: ",
        "select_language": "Выберите язык:",
        "select_exchange": "Выберите биржу:",
        "select_market": "Выберите рынок:",
        "select_type": "Тип уведомлений:",
        "select_threshold": "Выберите порог %:",
        "select_time": "Выберите таймфрейм:",
        "main_menu": [["🌐 Язык", "⚙️ Настройки"], ["📈 Биржа", "🕹 Рынок"], ["📊 Порог", "⏱ Время"]],
        "exchanges": ["Binance", "Bybit", "MEXC", "BingX"],
        "markets": ["Спот", "Фьючерсы"],
        "types": ["Памп", "Дамп", "Оба"],
        "thresholds": ["1%", "3%", "5%"],
        "timeframes": ["30с", "1м", "5м"]
    },
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your current settings:",
        "confirm": "✅ You selected: ",
        "select_language": "Choose language:",
        "select_exchange": "Choose exchange:",
        "select_market": "Choose market:",
        "select_type": "Type of alerts:",
        "select_threshold": "Choose threshold %:",
        "select_time": "Choose timeframe:",
        "main_menu": [["🌐 Language", "⚙️ Settings"], ["📈 Exchange", "🕹 Market"], ["📊 Threshold", "⏱ Time"]],
        "exchanges": ["Binance", "Bybit", "MEXC", "BingX"],
        "markets": ["Spot", "Futures"],
        "types": ["Pump", "Dump", "Both"],
        "thresholds": ["1%", "3%", "5%"],
        "timeframes": ["30s", "1m", "5m"]
    }
}

# === KEYBOARDS ===
def get_keyboard(lang):
    return ReplyKeyboardMarkup(texts[lang]["main_menu"], resize_keyboard=True)

# === MONITORING THREAD ===
def monitor_prices():
    while True:
        time.sleep(30)
        for user_id, data in user_data.items():
            if not data.get("verified"):
                continue

            lang = data.get("lang", "en")
            exchange = data.get("exchange", "Binance")
            market = data.get("market", "spot").lower()
            threshold = int(data.get("threshold", 3))
            timeframe = int(data.get("timeframe", 1))

            try:
                if exchange == "Binance":
                    url = "https://fapi.binance.com/fapi/v1/ticker/24hr" if market == "futures" else "https://api.binance.com/api/v3/ticker/24hr"
                    response = requests.get(url)
                    coins = response.json()

                    for coin in coins:
                        price_change = float(coin.get("priceChangePercent", 0))
                        symbol = coin.get("symbol", "")
                        if abs(price_change) >= threshold:
                            change_type = "📈 Pump" if price_change > 0 else "📉 Dump"
                            message = f"{change_type}: {symbol}\nChange: {price_change:.2f}%"
                            bot.send_message(chat_id=user_id, text=message)
                # TODO: Add Bybit, MEXC, BingX
            except Exception as e:
                logger.error(f"Monitoring error: {e}")

threading.Thread(target=monitor_prices, daemon=True).start()

# === HANDLERS ===
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "verified": False, "lang": "en", "exchange": "Binance",
        "market": "spot", "threshold": 3, "timeframe": 1
    }
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texts["en"]["start"],
        reply_markup=ReplyKeyboardMarkup([["✅ I'm not a bot"]], resize_keyboard=True)
    )

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text
    data = user_data.get(user_id, {})
    lang = data.get("lang", "en")

    if not data.get("verified"):
        if message in ["✅ I'm not a bot", "✅ Я не бот"]:
            user_data[user_id]["verified"] = True
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=texts[lang]["captcha_passed"],
                reply_markup=get_keyboard(lang)
            )
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["start"])
        return

    if message in ["🌐 Язык", "🌐 Language"]:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texts[lang]["select_language"],
            reply_markup=ReplyKeyboardMarkup([["Русский", "English"]], resize_keyboard=True)
        )
    elif message in ["Русский", "English"]:
        user_data[user_id]["lang"] = "ru" if message == "Русский" else "en"
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[user_data[user_id]["lang"]]["language_selected"], reply_markup=get_keyboard(user_data[user_id]["lang"]))
    elif message in ["⚙️ Настройки", "⚙️ Settings"]:
        current = user_data[user_id]
        text = texts[lang]["settings"] + f"\n\n🌐 Language: {lang.upper()}\n📈 Exchange: {current['exchange']}\n🕹 Market: {current['market']}\n📊 Threshold: {current['threshold']}%\n⏱ Timeframe: {current['timeframe']}m"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    elif message in ["📈 Биржа", "📈 Exchange"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["select_exchange"], reply_markup=ReplyKeyboardMarkup([[e] for e in texts[lang]["exchanges"]], resize_keyboard=True))
    elif message in texts[lang]["exchanges"]:
        user_data[user_id]["exchange"] = message
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["confirm"] + message, reply_markup=get_keyboard(lang))
    elif message in ["🕹 Рынок", "🕹 Market"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["select_market"], reply_markup=ReplyKeyboardMarkup([[m] for m in texts[lang]["markets"]], resize_keyboard=True))
    elif message in texts[lang]["markets"]:
        user_data[user_id]["market"] = "spot" if "Спот" in message or "Spot" in message else "futures"
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["confirm"] + message, reply_markup=get_keyboard(lang))
    elif message in ["📊 Порог", "📊 Threshold"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["select_threshold"], reply_markup=ReplyKeyboardMarkup([[p] for p in texts[lang]["thresholds"]], resize_keyboard=True))
    elif "%" in message:
        user_data[user_id]["threshold"] = int(message.strip("%"))
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["confirm"] + message, reply_markup=get_keyboard(lang))
    elif message in ["⏱ Время", "⏱ Time"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["select_time"], reply_markup=ReplyKeyboardMarkup([[t] for t in texts[lang]["timeframes"]], resize_keyboard=True))
    elif any(t in message for t in ["с", "s", "м", "m"]):
        num = ''.join(filter(str.isdigit, message))
        user_data[user_id]["timeframe"] = int(num)
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["confirm"] + message, reply_markup=get_keyboard(lang))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["confirm"] + message)

# === WEBHOOK ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot running"

# === MAIN ===
def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
