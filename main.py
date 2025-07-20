import logging
import json
import time
import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler,
    Filters, CallbackContext
)
from apscheduler.schedulers.background import BackgroundScheduler

# ===================== CONFIG =====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = 8443

# ===================== GLOBALS =====================
user_settings = {}  # user_id: settings dict
scheduler = BackgroundScheduler()
scheduler.start()

LANGS = {"en": "English", "ru": "Русский"}
DEFAULT_SETTINGS = {
    "language": "en",
    "exchange": "Binance",
    "interval": 60,
    "threshold": 3.0,
    "notify_type": "both"
}

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== LANG TEXT =====================
TEXTS = {
    "en": {
        "start": "Welcome! Please verify you're human.",
        "verified": "✅ Verified!",
        "menu": "Choose your settings:",
        "settings": "⚙️ Your Settings:
Exchange: {exchange}
Interval: {interval}s
Threshold: {threshold}%
Notify: {notify_type}",
        "select_language": "🌐 Choose your language:",
        "selected": "✅ Selected: {option}"
    },
    "ru": {
        "start": "Добро пожаловать! Подтвердите, что вы человек.",
        "verified": "✅ Верификация пройдена!",
        "menu": "Выберите настройки:",
        "settings": "⚙️ Ваши настройки:
Биржа: {exchange}
Интервал: {interval}с
Порог: {threshold}%
Уведомления: {notify_type}",
        "select_language": "🌐 Выберите язык:",
        "selected": "✅ Вы выбрали: {option}"
    }
}

# ===================== UTILS =====================
def get_user_language(user_id):
    return user_settings.get(user_id, DEFAULT_SETTINGS).get("language", "en")

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    return TEXTS[lang][key].format(**kwargs)

def build_settings_keyboard(user_id):
    lang = get_user_language(user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Binance", callback_data="exchange_Binance"),
         InlineKeyboardButton("📉 Bybit", callback_data="exchange_Bybit")],
        [InlineKeyboardButton("📊 MEXC", callback_data="exchange_MEXC"),
         InlineKeyboardButton("💹 BingX", callback_data="exchange_BingX")],
        [InlineKeyboardButton("⏱ Interval", callback_data="interval"),
         InlineKeyboardButton("📐 Threshold", callback_data="threshold")],
        [InlineKeyboardButton("🔔 Notify type", callback_data="notify"),
         InlineKeyboardButton("🌐 Language", callback_data="language")],
        [InlineKeyboardButton("ℹ️ Status", callback_data="status")]
    ])

# ===================== HANDLERS =====================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_settings[user_id] = DEFAULT_SETTINGS.copy()
    keyboard = [[InlineKeyboardButton("✅ I'm human", callback_data="verify")]]
    update.message.reply_text(get_text(user_id, "start"), reply_markup=InlineKeyboardMarkup(keyboard))

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    settings = user_settings.get(user_id, DEFAULT_SETTINGS)

    if data == "verify":
        query.edit_message_text(get_text(user_id, "verified"))
        context.bot.send_message(chat_id=user_id, text=get_text(user_id, "menu"), reply_markup=build_settings_keyboard(user_id))
        scheduler.add_job(check_price, 'interval', seconds=settings["interval"], args=[context, user_id], id=str(user_id), replace_existing=True)
    elif data.startswith("exchange_"):
        settings["exchange"] = data.split("_")[1]
    elif data == "interval":
        settings["interval"] = 60
    elif data == "threshold":
        settings["threshold"] = 3.0
    elif data == "notify":
        settings["notify_type"] = "both"
    elif data == "language":
        settings["language"] = "ru" if settings["language"] == "en" else "en"
    elif data == "status":
        text = get_text(user_id, "settings", **settings)
        context.bot.send_message(chat_id=user_id, text=text)
        return

    query.answer(get_text(user_id, "selected", option=data.split("_")[-1] if "_" in data else data))
    query.edit_message_text(get_text(user_id, "menu"), reply_markup=build_settings_keyboard(user_id))

async def fetch_price(exchange: str):
    urls = {
        "Binance": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "Bybit": "https://api.bybit.com/v2/public/tickers?symbol=BTCUSDT",
        "MEXC": "https://api.mexc.com/api/v3/ticker/price?symbol=BTCUSDT",
        "BingX": "https://bingx-api.example.com"  # Replace with real API
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(urls[exchange]) as resp:
                return await resp.json()
    except Exception as e:
        logger.warning(f"Error fetching price from {exchange}: {e}")
        return None

last_price = {}

def check_price(context: CallbackContext, user_id: int):
    settings = user_settings.get(user_id, DEFAULT_SETTINGS)
    exchange = settings["exchange"]
    threshold = settings["threshold"]
    notify_type = settings["notify_type"]

    async def fetch_and_compare():
        data = await fetch_price(exchange)
        if data is None:
            return

        price = None
        if exchange == "Binance" or exchange == "MEXC":
            price = float(data["price"])
        elif exchange == "Bybit":
            price = float(data["result"][0]["last_price"])
        if price is None:
            return

        old = last_price.get(user_id)
        last_price[user_id] = price

        if old:
            change = ((price - old) / old) * 100
            notify = (
                (notify_type == "pump" and change > threshold) or
                (notify_type == "dump" and change < -threshold) or
                (notify_type == "both" and abs(change) > threshold)
            )
            if notify:
                msg = f"🔔 {exchange}: {'📈' if change > 0 else '📉'} {change:.2f}%
Price: {price}$"
                context.bot.send_message(chat_id=user_id, text=msg)

    import asyncio
    asyncio.run(fetch_and_compare())

# ===================== MAIN =====================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )
    updater.idle()

if __name__ == "__main__":
    main()
