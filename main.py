import logging
import os
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, Dispatcher
)
from apscheduler.schedulers.background import BackgroundScheduler

# ================ CONFIG ====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 8443))
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)
logging.basicConfig(level=logging.INFO)
scheduler = BackgroundScheduler()
scheduler.start()

# ================ USER DATA ====================
user_data = {}

# ================ TEXTS ====================
texts = {
    "ru": {
        "start": "👋 Привет! Пройди капчу, чтобы продолжить.",
        "captcha_passed": "✅ Верификация прошла успешно!",
        "language_selected": "🌐 Язык установлен: Русский",
        "menu": "👇 Выбери действие:",
        "settings": "⚙️ Ваши настройки:",
        "confirm": "✅ Вы выбрали: ",
        "select_lang": "🌐 Выберите язык:",
        "select_exchange": "📈 Выберите биржу:",
        "select_market": "📊 Выберите рынок:",
        "select_notify_type": "🔔 Тип уведомлений:",
        "select_tf": "⏱ Интервал:",
        "select_threshold": "📉 Порог (%):",
        "main_menu": [["🌐 Язык", "⚙️ Настройки"], ["📈 Биржа", "📊 Рынок"], ["🔔 Уведомления"]],
        "not_verified": "🚫 Сначала подтвердите CAPTCHA.",
        "current_settings": "⚙️ Текущие настройки:
Биржа: {exchange}
Рынок: {market}
%: {threshold}%
Интервал: {interval} сек
Тип: {notif}",
    },
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your Settings:",
        "confirm": "✅ You selected: ",
        "select_lang": "🌐 Choose a language:",
        "select_exchange": "📈 Choose an exchange:",
        "select_market": "📊 Choose market type:",
        "select_notify_type": "🔔 Notification type:",
        "select_tf": "⏱ Timeframe:",
        "select_threshold": "📉 Threshold (%):",
        "main_menu": [["🌐 Language", "⚙️ Settings"], ["📈 Exchange", "📊 Market"], ["🔔 Notifications"]],
        "not_verified": "🚫 Please complete CAPTCHA first.",
        "current_settings": "⚙️ Current Settings:
Exchange: {exchange}
Market: {market}
%: {threshold}%
Interval: {interval} sec
Type: {notif}",
    },
}

exchanges = ["Binance", "Bybit", "MEXC", "BingX"]
markets = {"ru": ["Спот", "Фьючерсы"], "en": ["Spot", "Futures"]}
notify_types = {"ru": ["Памп", "Дамп", "Оба"], "en": ["Pump", "Dump", "Both"]}
intervals = ["30", "60", "120"]
thresholds = ["1", "2", "5", "10"]

# ================ KEYBOARD ====================
def get_keyboard(lang):
    return ReplyKeyboardMarkup(texts[lang]["main_menu"], resize_keyboard=True)

# ================ CAPTCHA & START ====================
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user_data[uid] = {
        "verified": False, "lang": "en", "exchange": "Binance", "market": "Spot",
        "notif": "Both", "interval": 60, "threshold": 2
    }
    context.bot.send_message(uid, texts["en"]["start"],
        reply_markup=ReplyKeyboardMarkup([["✅ I'm not a bot"]], resize_keyboard=True))

# ================ HANDLER ====================
def handle_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    msg = update.message.text
    data = user_data.get(uid, {})
    lang = data.get("lang", "en")

    # CAPTCHA
    if not data.get("verified"):
        if msg in ["✅ I'm not a bot", "✅ Я не бот"]:
            user_data[uid]["verified"] = True
            context.bot.send_message(uid, texts[lang]["captcha_passed"], reply_markup=get_keyboard(lang))
        else:
            context.bot.send_message(uid, texts[lang]["not_verified"])
        return

    # LANGUAGE
    if msg in ["🌐 Language", "🌐 Язык"]:
        kb = [["English", "Русский"]]
        context.bot.send_message(uid, texts[lang]["select_lang"],
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    elif msg in ["English", "Русский"]:
        new_lang = "ru" if msg == "Русский" else "en"
        user_data[uid]["lang"] = new_lang
        context.bot.send_message(uid, texts[new_lang]["language_selected"],
            reply_markup=get_keyboard(new_lang))
    elif msg in ["⚙️ Settings", "⚙️ Настройки"]:
        d = user_data[uid]
        s = texts[lang]["current_settings"].format(
            exchange=d["exchange"], market=d["market"],
            threshold=d["threshold"], interval=d["interval"],
            notif=d["notif"]
        )
        context.bot.send_message(uid, s, reply_markup=get_keyboard(lang))
    elif msg in ["📈 Exchange", "📈 Биржа"]:
        context.bot.send_message(uid, texts[lang]["select_exchange"],
            reply_markup=ReplyKeyboardMarkup([[e] for e in exchanges], resize_keyboard=True))
    elif msg in exchanges:
        user_data[uid]["exchange"] = msg
        context.bot.send_message(uid, texts[lang]["confirm"] + msg, reply_markup=get_keyboard(lang))
    elif msg in ["📊 Market", "📊 Рынок"]:
        context.bot.send_message(uid, texts[lang]["select_market"],
            reply_markup=ReplyKeyboardMarkup([[m] for m in markets[lang]], resize_keyboard=True))
    elif msg in markets[lang]:
        user_data[uid]["market"] = msg
        context.bot.send_message(uid, texts[lang]["confirm"] + msg, reply_markup=get_keyboard(lang))
    elif msg in ["🔔 Notifications", "🔔 Уведомления"]:
        context.bot.send_message(uid, texts[lang]["select_notify_type"],
            reply_markup=ReplyKeyboardMarkup([[t] for t in notify_types[lang]], resize_keyboard=True))
    elif msg in notify_types[lang]:
        user_data[uid]["notif"] = msg
        context.bot.send_message(uid, texts[lang]["select_tf"],
            reply_markup=ReplyKeyboardMarkup([[i] for i in intervals], resize_keyboard=True))
    elif msg in intervals:
        user_data[uid]["interval"] = int(msg)
        context.bot.send_message(uid, texts[lang]["select_threshold"],
            reply_markup=ReplyKeyboardMarkup([[t] for t in thresholds], resize_keyboard=True))
    elif msg in thresholds:
        user_data[uid]["threshold"] = float(msg)
        context.bot.send_message(uid, texts[lang]["confirm"] + msg + " %", reply_markup=get_keyboard(lang))
    else:
        context.bot.send_message(uid, texts[lang]["confirm"] + msg, reply_markup=get_keyboard(lang))

# ================ MONITORING ====================
def fetch_price(exchange, market, symbol="BTCUSDT"):
    try:
        if exchange == "Binance":
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            return float(requests.get(url, timeout=5).json()["price"])
        # Реализация аналогично для Bybit, MEXC, BingX
    except Exception as e:
        logging.warning(f"{exchange} error: {e}")
        return None

def monitor_prices():
    for uid, data in user_data.items():
        if not data.get("verified"):
            continue
        exchange = data["exchange"]
        symbol = "BTCUSDT"  # можно расширить
        market = data["market"]
        notif = data["notif"]
        interval = data["interval"]
        threshold = data["threshold"]

        current = fetch_price(exchange, market, symbol)
        prev = data.get("prev_price", current)
        if not current or not prev:
            continue

        diff = ((current - prev) / prev) * 100
        data["prev_price"] = current

        lang = data["lang"]
        is_pump = diff >= threshold
        is_dump = diff <= -threshold

        if (notif in ["Pump", "Памп", "Both", "Оба"] and is_pump) or            (notif in ["Dump", "Дамп", "Both", "Оба"] and is_dump):
            direction = "📈 Памп" if is_pump else "📉 Дамп"
            msg = f"{direction} на {exchange} ({market}):
Цена: {current:.2f}
Изменение: {diff:.2f}%"
            bot.send_message(uid, msg)

scheduler.add_job(monitor_prices, "interval", seconds=30)

# ================ FLASK ====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running."

def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
