import logging
import json
import time
import threading
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler

# Установи свой BOT TOKEN здесь
TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"


# ===================== CONFIG =====================
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"  # <-- ваш Render-домен

WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = 8443

# Стартовый логгер
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище пользователей
user_data = {}

# Биржи
SUPPORTED_EXCHANGES = ["Binance", "Bybit", "MEXC", "BingX", "KuCoin", "OKX"]

# Данные по умолчанию
DEFAULT_USER_SETTINGS = {
    "language": "ru",
    "exchange": "Binance",
    "interval": 60,
    "threshold": 2,
    "verified": False,
    "notify_type": "both"
}

# Переводы
LANG = {
    "ru": {
        "welcome": "👋 Добро пожаловать! Пройдите CAPTCHA:",
        "verified": "✅ Вы верифицированы!",
        "choose_exchange": "Выберите биржу:",
        "choose_interval": "Выберите интервал:",
        "choose_threshold": "Выберите порог:",
        "choose_notify": "Тип уведомлений:",
        "menu": "⚙ Настройки",
        "back": "🔙 Назад",
        "pumps": "📈 Только пампы",
        "dumps": "📉 Только дампы",
        "both": "📊 Всё"
    },
    "en": {
        "welcome": "👋 Welcome! Please pass the CAPTCHA:",
        "verified": "✅ You are verified!",
        "choose_exchange": "Choose exchange:",
        "choose_interval": "Choose interval:",
        "choose_threshold": "Choose threshold:",
        "choose_notify": "Notification type:",
        "menu": "⚙ Settings",
        "back": "🔙 Back",
        "pumps": "📈 Pumps only",
        "dumps": "📉 Dumps only",
        "both": "📊 Both"
    }
}

# Генерация CAPTCHA (emoji)
def generate_captcha():
    return "👍"

# Обработка старта
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    user_data[uid] = DEFAULT_USER_SETTINGS.copy()
    user_data[uid]["captcha"] = generate_captcha()
    lang = user_data[uid]["language"]
    keyboard = [[InlineKeyboardButton(user_data[uid]["captcha"], callback_data="captcha_passed")]]
    update.message.reply_text(LANG[lang]["welcome"], reply_markup=InlineKeyboardMarkup(keyboard))

# CAPTCHA-подтверждение
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    uid = query.from_user.id

    if uid not in user_data:
        user_data[uid] = DEFAULT_USER_SETTINGS.copy()

    if query.data == "captcha_passed":
        user_data[uid]["verified"] = True
        lang = user_data[uid]["language"]
        query.edit_message_text(text=LANG[lang]["verified"])
        show_main_menu(query, uid)
    elif query.data.startswith("exchange_"):
        user_data[uid]["exchange"] = query.data.split("_")[1]
        show_main_menu(query, uid)
    elif query.data.startswith("interval_"):
        user_data[uid]["interval"] = int(query.data.split("_")[1])
        show_main_menu(query, uid)
    elif query.data.startswith("threshold_"):
        user_data[uid]["threshold"] = int(query.data.split("_")[1])
        show_main_menu(query, uid)
    elif query.data.startswith("notify_"):
        user_data[uid]["notify_type"] = query.data.split("_")[1]
        show_main_menu(query, uid)
    elif query.data == "settings":
        show_settings_menu(query, uid)
    elif query.data == "back":
        show_main_menu(query, uid)

# Главное меню
def show_main_menu(query, uid):
    lang = user_data[uid]["language"]
    buttons = [
        [InlineKeyboardButton(LANG[lang]["choose_exchange"], callback_data="settings")],
        [InlineKeyboardButton(LANG[lang]["menu"], callback_data="settings")]
    ]
    query.message.reply_text("📊 Мониторинг включен!", reply_markup=InlineKeyboardMarkup(buttons))

# Меню настроек
def show_settings_menu(query, uid):
    lang = user_data[uid]["language"]
    buttons = [
        [InlineKeyboardButton(exchange, callback_data=f"exchange_{exchange}")] for exchange in SUPPORTED_EXCHANGES
    ] + [
        [InlineKeyboardButton("30s", callback_data="interval_30"),
         InlineKeyboardButton("1m", callback_data="interval_60"),
         InlineKeyboardButton("5m", callback_data="interval_300")],
        [InlineKeyboardButton("1%", callback_data="threshold_1"),
         InlineKeyboardButton("2%", callback_data="threshold_2"),
         InlineKeyboardButton("5%", callback_data="threshold_5")],
        [InlineKeyboardButton(LANG[lang]["pumps"], callback_data="notify_pumps"),
         InlineKeyboardButton(LANG[lang]["dumps"], callback_data="notify_dumps"),
         InlineKeyboardButton(LANG[lang]["both"], callback_data="notify_both")],
        [InlineKeyboardButton(LANG[lang]["back"], callback_data="back")]
    ]
    query.message.reply_text(LANG[lang]["choose_exchange"], reply_markup=InlineKeyboardMarkup(buttons))

# Мониторинг изменений цены (заглушка)
def monitor():
    while True:
        for uid, data in user_data.items():
            if data["verified"]:
                # Пример запроса к API биржи (только Binance здесь)
                if data["exchange"] == "Binance":
                    try:
                        resp = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr")
                        market_data = resp.json()
                        if isinstance(market_data, list):
                            pass  # Здесь логика уведомлений
                        else:
                            logging.warning("Unexpected data format")
                    except Exception as e:
                        logging.warning(f"Monitor error: {e}")
        time.sleep(15)

# Точка входа
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))

    # Запуск мониторинга в отдельном потоке
    t = threading.Thread(target=monitor)
    t.start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

app = Flask(__name__)

updater.start_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=WEBHOOK_URL,
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
