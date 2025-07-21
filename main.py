import logging
import os
import time
import threading
import requests
from flask import Flask, request
from telegram import (
    Bot, Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
)

# === CONFIG ===
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

# === DATA ===
user_data = {}

SUPPORTED_EXCHANGES = ['Binance', 'Bybit', 'MEXC', 'BingX']
SUPPORTED_MARKETS = ['Spot', 'Futures']
TIMEFRAMES = ['30s', '1m', '5m', '15m']
PUMP_TYPES = ['📈 Pump', '📉 Dump', '📊 Both']

# === TRANSLATIONS ===
texts = {
    "ru": {
        "start": "👋 Привет! Пройди капчу, чтобы продолжить.",
        "captcha_passed": "✅ Верификация прошла успешно!",
        "language_selected": "🌐 Язык установлен: Русский",
        "menu": "👇 Выберите действие:",
        "settings": "⚙️ Ваши настройки:",
        "confirm": "✅ Вы выбрали: ",
        "current": "🛠 Текущие настройки:",
        "exchange": "📊 Выберите биржу:",
        "market": "💹 Выберите рынок:",
        "timeframe": "⏱ Интервал времени:",
        "threshold": "📈 Порог изменения (%):",
        "alerts": "🔔 Тип уведомлений:",
        "main_menu": [["🌐 Язык", "⚙️ Настройки"], ["📊 Биржа", "💹 Рынок"], ["📈 Порог", "⏱ Интервал"], ["🔔 Уведомления"]],
        "captcha_button": "✅ Я не бот"
    },
    "en": {
        "start": "👋 Hello! Please verify CAPTCHA to continue.",
        "captcha_passed": "✅ Verification successful!",
        "language_selected": "🌐 Language set to: English",
        "menu": "👇 Choose an action:",
        "settings": "⚙️ Your Settings:",
        "confirm": "✅ You selected: ",
        "current": "🛠 Current settings:",
        "exchange": "📊 Select exchange:",
        "market": "💹 Select market:",
        "timeframe": "⏱ Timeframe:",
        "threshold": "📈 Threshold (%):",
        "alerts": "🔔 Alert type:",
        "main_menu": [["🌐 Language", "⚙️ Settings"], ["📊 Exchange", "💹 Market"], ["📈 Threshold", "⏱ Timeframe"], ["🔔 Alerts"]],
        "captcha_button": "✅ I'm not a bot"
    }
}
# === UTILS ===
def get_lang(user_id):
    return user_data.get(user_id, {}).get("lang", "en")


def t(user_id, key):
    lang = get_lang(user_id)
    return texts.get(lang, texts["en"]).get(key, key)


def get_reply_keyboard(user_id):
    lang = get_lang(user_id)
    return ReplyKeyboardMarkup(texts[lang]["main_menu"], resize_keyboard=True)


def init_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "verified": False,
            "lang": "en",
            "exchange": "Binance",
            "market": "Spot",
            "timeframe": "1m",
            "threshold": 3,
            "alerts": "📊 Both"
        }

# === CAPTCHA ===
def send_captcha(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    init_user(user_id)
    keyboard = [[KeyboardButton(t(user_id, "captcha_button"))]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(t(user_id, "start"), reply_markup=reply_markup)

def verify_captcha(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    text = update.message.text
    if text == t(user_id, "captcha_button"):
        user_data[user_id]["verified"] = True
        update.message.reply_text(t(user_id, "captcha_passed"), reply_markup=get_reply_keyboard(user_id))
    else:
        send_captcha(update, context)
        # === ОБРАБОТЧИКИ КНОПОК ===
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    text = update.message.text
    init_user(user_id)

    if not user_data[user_id]["verified"]:
        return send_captcha(update, context)

    if text == t(user_id, "language"):
        keyboard = [[KeyboardButton("🇬🇧 English")], [KeyboardButton("🇷🇺 Русский")]]
        update.message.reply_text(t(user_id, "choose_lang"), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text in ["🇬🇧 English", "🇷🇺 Русский"]:
        user_data[user_id]["lang"] = "en" if "English" in text else "ru"
        update.message.reply_text(t(user_id, "language_selected"), reply_markup=get_reply_keyboard(user_id))
        return

    if text == t(user_id, "exchange"):
        keyboard = [
            [KeyboardButton("Binance"), KeyboardButton("Bybit")],
            [KeyboardButton("MEXC"), KeyboardButton("BingX")]
        ]
        update.message.reply_text(t(user_id, "choose_exchange"), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text in ["Binance", "Bybit", "MEXC", "BingX"]:
        user_data[user_id]["exchange"] = text
        update.message.reply_text(t(user_id, "confirm_exchange").format(exchange=text), reply_markup=get_reply_keyboard(user_id))
        return

    if text == t(user_id, "market"):
        keyboard = [[KeyboardButton("Spot"), KeyboardButton("Futures")]]
        update.message.reply_text(t(user_id, "choose_market"), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text in ["Spot", "Futures"]:
        user_data[user_id]["market"] = text
        update.message.reply_text(t(user_id, "confirm_market").format(market=text), reply_markup=get_reply_keyboard(user_id))
        return

    if text == t(user_id, "threshold"):
        keyboard = [
            [KeyboardButton("1%"), KeyboardButton("3%")],
            [KeyboardButton("5%"), KeyboardButton("10%")]
        ]
        update.message.reply_text(t(user_id, "choose_threshold"), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text.endswith("%"):
        try:
            value = int(text.replace("%", ""))
            user_data[user_id]["threshold"] = value
            update.message.reply_text(t(user_id, "confirm_threshold").format(threshold=value), reply_markup=get_reply_keyboard(user_id))
        except:
            pass

# return тут был лишним или стоял не в том месте — удаляем

if text == t(user_id, "interval"):
    keyboard = [
        [KeyboardButton("30s"), KeyboardButton("1m")],
        [KeyboardButton("5m"), KeyboardButton("15m")]
    ]
    update.message.reply_text(
        t(user_id, "choose_interval"),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return

    if text.endswith("s") or text.endswith("m"):
        try:
            unit = text[-1]
            value = int(text[:-1])
            seconds = value * 60 if unit == "m" else value
            user_data[user_id]["interval"] = seconds
            update.message.reply_text(t(user_id, "confirm_interval").format(interval=text), reply_markup=get_reply_keyboard(user_id))
        except:
            pass
        return

    if text == t(user_id, "alerts"):
        keyboard = [
            [KeyboardButton(t(user_id, "alert_pump"))],
            [KeyboardButton(t(user_id, "alert_dump"))],
            [KeyboardButton(t(user_id, "alert_both"))]
        ]
        update.message.reply_text(t(user_id, "choose_alert_type"), reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text in [t(user_id, "alert_pump"), t(user_id, "alert_dump"), t(user_id, "alert_both")]:
        if text == t(user_id, "alert_pump"):
            user_data[user_id]["alerts"] = "pump"
        elif text == t(user_id, "alert_dump"):
            user_data[user_id]["alerts"] = "dump"
        else:
            user_data[user_id]["alerts"] = "both"
        update.message.reply_text(t(user_id, "confirm_alerts").format(alerts=text), reply_markup=get_reply_keyboard(user_id))
        return

    if text == t(user_id, "settings"):
        settings_msg = (
            f"{t(user_id, 'language')}: {'🇬🇧 English' if user_data[user_id]['lang'] == 'en' else '🇷🇺 Русский'}\n"
            f"{t(user_id, 'exchange')}: {user_data[user_id]['exchange']}\n"
            f"{t(user_id, 'market')}: {user_data[user_id]['market']}\n"
            f"{t(user_id, 'threshold')}: {user_data[user_id]['threshold']}%\n"
            f"{t(user_id, 'interval')}: {user_data[user_id]['interval']}s\n"
            f"{t(user_id, 'alerts')}: {user_data[user_id]['alerts']}\n"
        )
        # Здесь заканчивается обработка команды или текста
update.message.reply_text(t(user_id, "start"), reply_markup=get_reply_keyboard(user_id))


# Отдельно — определение функции, без лишнего отступа
def monitor_prices():
    while True:
        for user_id, settings in user_data.items():
            try:
                symbol_changes = get_market_changes(
                    exchange=settings["exchange"],
                    market_type=settings["market"],
                    threshold=settings["threshold"],
                    interval=settings["interval"]
                )

                if symbol_changes:
                    for sym, change in symbol_changes.items():
                        print(f"{sym}: {change}")
            except:
                pass
                        print(f"{sym}: {change}")
            except:
                pass
                        if settings["alerts"] == "pump" and change < 0:
                            continue
                        if settings["alerts"] == "dump" and change > 0:
                            continue
                        alert_msg = f"💹 {sym}:\n{change:.2f}% in last {settings['interval']}s"
                        context.bot.send_message(chat_id=user_id, text=alert_msg)
            except Exception as e:
                print(f"Error in monitor_prices: {e}")
        time.sleep(30)

def get_market_changes(exchange, market_type, threshold, interval):
    try:
        # Пример: добавить API-интеграцию под каждую биржу (ниже только шаблон для Binance)
        if exchange == "Binance":
            url = "https://api.binance.com/api/v3/ticker/24hr"
            response = requests.get(url, timeout=10)
            data = response.json()
            result = {}
            for item in data:
                symbol = item.get("symbol")
                if market_type == "spot" and not symbol.endswith("USDT"):
                    continue
                price_change = float(item.get("priceChangePercent", 0))
                if abs(price_change) >= threshold:
                    result[symbol] = price_change
            return result
        # Здесь будет расширение для Bybit, MEXC, BingX
    except Exception as e:
        print(f"Error in get_market_changes: {e}")
    return {}
    # === Запуск Flask и Telegram бота ===

@app.route('/')
def index():
    return 'Bot is running.'

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def run_telegram():
    updater.start_polling()
    updater.idle()

# === Запуск мониторинга цен в отдельном потоке ===

price_thread = threading.Thread(target=monitor_prices, daemon=True)
price_thread.start()

# === Запуск сервера и Telegram-бота ===

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    run_telegram()
