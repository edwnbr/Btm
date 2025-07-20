import logging
import os
import threading
import time
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
)

BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 8443))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

logging.basicConfig(level=logging.INFO)

user_data = {}

# ===== ТЕКСТЫ =====
texts = {
    "ru": {
        "start": "👋 Привет! Подтверди, что ты не бот.",
        "captcha_passed": "✅ Верификация успешна!",
        "select_action": "👇 Выберите действие:",
        "settings": "⚙️ Ваши настройки:",
        "language_set": "🌐 Язык: Русский",
        "menu": [["🌐 Язык", "⚙️ Настройки"], ["📊 Биржа", "📈 Рынок"], ["⏱ Интервал", "📉 Порог"]],
    },
    "en": {
        "start": "👋 Hello! Please confirm you're not a bot.",
        "captcha_passed": "✅ Verification passed!",
        "select_action": "👇 Choose an action:",
        "settings": "⚙️ Your settings:",
        "language_set": "🌐 Language: English",
        "menu": [["🌐 Language", "⚙️ Settings"], ["📊 Exchange", "📈 Market"], ["⏱ Interval", "📉 Threshold"]],
    }
}

def get_keyboard(lang):
    return ReplyKeyboardMarkup(
        texts[lang]["menu"], resize_keyboard=True, one_time_keyboard=False
    )

# ===== ОБРАБОТЧИК /start =====
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {
        "verified": False, "lang": "en", "exchange": "Binance",
        "market": "spot", "threshold": 2.0, "interval": 5
    }
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texts["en"]["start"],
        reply_markup=ReplyKeyboardMarkup([["✅ I'm not a bot"]], resize_keyboard=True)
    )

# ===== ОБРАБОТКА ТЕКСТА =====
def handle_text(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    msg = update.message.text
    user = user_data.get(uid, {})
    lang = user.get("lang", "en")

    if not user.get("verified"):
        if msg in ["✅ I'm not a bot", "✅ Я не бот"]:
            user["verified"] = True
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=texts[lang]["captcha_passed"],
                reply_markup=get_keyboard(lang)
            )
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❗ Complete CAPTCHA first." if lang == "en" else "❗ Сначала пройди капчу."
            )
        return

    if msg in ["🌐 Language", "🌐 Язык"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Choose / Выберите:", reply_markup=ReplyKeyboardMarkup([["English", "Русский"]], resize_keyboard=True))
    elif msg in ["English", "Русский"]:
        user["lang"] = "ru" if msg == "Русский" else "en"
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[user["lang"]]["language_set"], reply_markup=get_keyboard(user["lang"]))
    elif msg in ["📊 Биржа", "📊 Exchange"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите биржу / Choose exchange:", reply_markup=ReplyKeyboardMarkup([["Binance", "Bybit"], ["MEXC", "BingX"]], resize_keyboard=True))
    elif msg in ["Binance", "Bybit", "MEXC", "BingX"]:
        user["exchange"] = msg
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Биржа: {msg}", reply_markup=get_keyboard(lang))
    elif msg in ["📈 Рынок", "📈 Market"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите тип / Select type:", reply_markup=ReplyKeyboardMarkup([["spot", "futures"]], resize_keyboard=True))
    elif msg in ["spot", "futures"]:
        user["market"] = msg
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Рынок: {msg}", reply_markup=get_keyboard(lang))
    elif msg in ["⏱ Интервал", "⏱ Interval"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Интервал в минутах (1-30):", reply_markup=ReplyKeyboardMarkup([[str(i)] for i in range(1, 6)], resize_keyboard=True))
    elif msg.isdigit() and 1 <= int(msg) <= 30:
        user["interval"] = int(msg)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Интервал: {msg} мин", reply_markup=get_keyboard(lang))
    elif msg in ["📉 Порог", "📉 Threshold"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Порог в % (1-20):", reply_markup=ReplyKeyboardMarkup([[str(i)] for i in range(1, 6)], resize_keyboard=True))
    elif msg.replace(".", "", 1).isdigit():
        user["threshold"] = float(msg)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Порог: {msg}%", reply_markup=get_keyboard(lang))
    elif msg in ["⚙️ Settings", "⚙️ Настройки"]:
        t = f"{texts[lang]['settings']}

📊 Биржа: {user.get('exchange')}
📈 Рынок: {user.get('market')}
⏱ Интервал: {user.get('interval')} мин
📉 Порог: {user.get('threshold')}%"
        context.bot.send_message(chat_id=update.effective_chat.id, text=t, reply_markup=get_keyboard(lang))

# ====== УВЕДОМЛЕНИЯ ПО API ======
def monitor_prices():
    while True:
        for uid, data in user_data.items():
            if not data.get("verified"):
                continue
            exchange = data["exchange"]
            market = data["market"]
            threshold = data["threshold"]
            interval = data["interval"]
            # Пример API (Binance spot)
            if exchange == "Binance":
                try:
                    url = "https://api.binance.com/api/v3/ticker/24hr"
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200 and isinstance(res.json(), list):
                        for coin in res.json():
                            symbol = coin["symbol"]
                            change = float(coin["priceChangePercent"])
                            if abs(change) >= threshold:
                                msg = f"📢 {symbol}
Изменение: {change:.2f}%"
                                bot.send_message(chat_id=uid, text=msg)
                except Exception as e:
                    logging.warning(f"Ошибка Binance API: {e}")
        time.sleep(60)

# ===== WEBHOOK =====
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    bot.set_webhook(url=WEBHOOK_URL)
    thread = threading.Thread(target=monitor_prices)
    thread.start()
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
