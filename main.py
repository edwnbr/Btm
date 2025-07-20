import logging
import json
import os
import time
import requests
import threading
import asyncio
import aiohttp
from flask import Flask, request
from telegram import (
    Bot,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    Dispatcher,
)
from apscheduler.schedulers.background import BackgroundScheduler

# ===================== CONFIG =====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"

WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = 8443

LANGUAGES = ["EN", "RU"]
DEFAULT_SETTINGS = {
    "language": "EN",
    "exchange": "Binance",
    "market_type": "spot",
    "alert_type": "both",
    "timeframe": "1m",
    "threshold": 1.0
}

LANG = {
    "EN": {
        "start": "â Please verify you're human:",
        "verified": "â Verified! Choose an option:",
        "select_lang": "ð Select language:",
        "main_menu": "Main Menu",
        "exchange_set": "ð Exchange set to:",
        "market_set": "ð Market type set to:",
        "alert_set": "ð Alert type set to:",
        "timeframe_set": "â±ï¸ Timeframe set to:",
        "threshold_set": "ð Threshold set to:",
        "settings": "âï¸ Your Settings:
",
        "pump": "ð Pump",
        "dump": "ð Dump"
    },
    "RU": {
        "start": "â ÐÐ¾Ð¶Ð°Ð»ÑÐ¹ÑÑÐ°, Ð¿Ð¾Ð´ÑÐ²ÐµÑÐ´Ð¸ÑÐµ, ÑÑÐ¾ Ð²Ñ Ð½Ðµ ÑÐ¾Ð±Ð¾Ñ:",
        "verified": "â ÐÐµÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¸Ñ Ð¿ÑÐ¾Ð¹Ð´ÐµÐ½Ð°! ÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¾Ð¿ÑÐ¸Ñ:",
        "select_lang": "ð ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº:",
        "main_menu": "ÐÐ»Ð°Ð²Ð½Ð¾Ðµ Ð¼ÐµÐ½Ñ",
        "exchange_set": "ð ÐÐ¸ÑÐ¶Ð° ÑÑÑÐ°Ð½Ð¾Ð²Ð»ÐµÐ½Ð°:",
        "market_set": "ð Ð¢Ð¸Ð¿ ÑÑÐ½ÐºÐ° ÑÑÑÐ°Ð½Ð¾Ð²Ð»ÐµÐ½:",
        "alert_set": "ð Ð¢Ð¸Ð¿ ÑÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸Ð¹:",
        "timeframe_set": "â±ï¸ Ð¢Ð°Ð¹Ð¼ÑÑÐµÐ¹Ð¼:",
        "threshold_set": "ð ÐÐ¾ÑÐ¾Ð³ Ð¸Ð·Ð¼ÐµÐ½ÐµÐ½Ð¸Ñ:",
        "settings": "âï¸ ÐÐ°ÑÐ¸ Ð½Ð°ÑÑÑÐ¾Ð¹ÐºÐ¸:
",
        "pump": "ð ÐÐ°Ð¼Ð¿",
        "dump": "ð ÐÐ°Ð¼Ð¿"
    }
}

# ===================== STORAGE =====================
users = {}
verified_users = set()
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# ===================== HELPERS =====================
def get_keyboard(lang):
    l = LANG[lang]
    return ReplyKeyboardMarkup([
        [KeyboardButton("ð Exchange"), KeyboardButton("ð Market")],
        [KeyboardButton("ð Alerts"), KeyboardButton("â±ï¸ Timeframe")],
        [KeyboardButton("ð Threshold"), KeyboardButton("âï¸ My Settings")],
        [KeyboardButton("ð Language")]
    ], resize_keyboard=True)

def get_user_settings(uid):
    if uid not in users:
        users[uid] = DEFAULT_SETTINGS.copy()
    return users[uid]

def fetch_price_from_binance():
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price")
        data = resp.json()
        if isinstance(data, list):
            return {item["symbol"]: float(item["price"]) for item in data if "price" in item}
    except Exception as e:
        logging.warning(f"Binance error: {e}")
    return {}

# ===================== HANDLERS =====================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    update.message.reply_text(LANG["EN"]["start"], reply_markup=ReplyKeyboardMarkup(
        [[KeyboardButton("â I'm human")]], resize_keyboard=True))
    users[user_id] = DEFAULT_SETTINGS.copy()

def verify(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    verified_users.add(user_id)
    lang = users[user_id]["language"]
    update.message.reply_text(LANG[lang]["verified"], reply_markup=get_keyboard(lang))

def text_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in verified_users:
        update.message.reply_text(LANG["EN"]["start"])
        return

    msg = update.message.text
    settings = get_user_settings(user_id)
    lang = settings["language"]
    l = LANG[lang]

    if msg == "ð Language":
        settings["language"] = "RU" if lang == "EN" else "EN"
        update.message.reply_text(l["select_lang"], reply_markup=get_keyboard(settings["language"]))
    elif msg == "ð Exchange":
        settings["exchange"] = "Bybit" if settings["exchange"] == "Binance" else "Binance"
        update.message.reply_text(f"{l['exchange_set']} {settings['exchange']}")
    elif msg == "ð Market":
        settings["market_type"] = "futures" if settings["market_type"] == "spot" else "spot"
        update.message.reply_text(f"{l['market_set']} {settings['market_type']}")
    elif msg == "ð Alerts":
        options = ["pump", "dump", "both"]
        current = options.index(settings["alert_type"])
        settings["alert_type"] = options[(current + 1) % 3]
        update.message.reply_text(f"{l['alert_set']} {settings['alert_type']}")
    elif msg == "â±ï¸ Timeframe":
        tfs = ["1m", "5m", "15m"]
        i = tfs.index(settings["timeframe"])
        settings["timeframe"] = tfs[(i + 1) % len(tfs)]
        update.message.reply_text(f"{l['timeframe_set']} {settings['timeframe']}")
    elif msg == "ð Threshold":
        thresholds = [0.5, 1.0, 2.0, 5.0]
        i = thresholds.index(settings["threshold"]) if settings["threshold"] in thresholds else 0
        settings["threshold"] = thresholds[(i + 1) % len(thresholds)]
        update.message.reply_text(f"{l['threshold_set']} {settings['threshold']}%")
    elif msg == "âï¸ My Settings":
        s = users[user_id]
        text = f"{l['settings']}"                f"
ð Language: {s['language']}"                f"
ð Exchange: {s['exchange']}"                f"
ð Market: {s['market_type']}"                f"
ð Alerts: {s['alert_type']}"                f"
â±ï¸ Timeframe: {s['timeframe']}"                f"
ð Threshold: {s['threshold']}%"
        update.message.reply_text(text)

# ===================== MONITOR =====================
prev_prices = {}

def monitor():
    global prev_prices
    current_prices = fetch_price_from_binance()
    if not current_prices:
        return

    for user_id in verified_users:
        s = get_user_settings(user_id)
        symbols = ["BTCUSDT", "ETHUSDT"]
        for sym in symbols:
            if sym in current_prices and sym in prev_prices:
                old = prev_prices[sym]
                new = current_prices[sym]
                change = ((new - old) / old) * 100
                threshold = s["threshold"]
                lang = s["language"]
                l = LANG[lang]
                if change >= threshold and s["alert_type"] in ["pump", "both"]:
                    bot.send_message(user_id, f"{l['pump']} {sym}: +{round(change, 2)}%")
                elif change <= -threshold and s["alert_type"] in ["dump", "both"]:
                    bot.send_message(user_id, f"{l['dump']} {sym}: {round(change, 2)}%")

    prev_prices = current_prices

# ===================== FLASK WEBHOOK =====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running"

# ===================== INIT =====================
updater = Updater(BOT_TOKEN, use_context=True)
dp: Dispatcher = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.regex("human"), verify))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

scheduler = BackgroundScheduler()
scheduler.add_job(monitor, "interval", seconds=30)
scheduler.start()

# Set webhook
bot.delete_webhook()
time.sleep(1)
bot.set_webhook(WEBHOOK_URL)

# Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
