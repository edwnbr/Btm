import os
import json
import time
import threading
import logging
import requests
import asyncio
import aiohttp

from flask import Flask, request
from telegram import (
    Bot, Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler
)

# === Инициализация переменных окружения ===
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TG_TOKEN")  # теперь токен берется из .env
APP_URL = os.getenv("APP_URL")  # домен render из .env

if not TOKEN:
    raise ValueError("TG_TOKEN переменная окружения не найдена.")

bot = Bot(token=TOKEN)

# === Flask + Dispatcher ===
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

# === Логирование ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === Языковые словари ===
translations = {
    'ru': {
        'language': "Язык",
        'exchange': "Биржа",
        'market': "Рынок",
        'timeframe': "Таймфрейм",
        'threshold': "Порог %",
        'notifications': "Оповещения",
        'settings': "Мои настройки",
        'analysis': "АИ анализ",
        'select_option': "Выберите параметр:",
        'back': "Назад",
        'spot': "Спот",
        'futures': "Фьючерсы",
        'pump': "Памп",
        'dump': "Дамп",
        'both': "Оба",
        'notify_type': "Тип уведомлений",
        'select_exchange': "Выберите биржу:",
        'select_market': "Выберите рынок:",
        'select_timeframe': "Выберите таймфрейм:",
        'select_threshold': "Выберите порог %:",
        'select_notify_type': "Выберите тип уведомлений:",
        'ai_result': "АИ анализ для {}: {}"
    },
    'en': {
        'language': "Language",
        'exchange': "Exchange",
        'market': "Market",
        'timeframe': "Timeframe",
        'threshold': "Threshold %",
        'notifications': "Notifications",
        'settings': "My Settings",
        'analysis': "AI Analysis",
        'select_option': "Choose setting:",
        'back': "Back",
        'spot': "Spot",
        'futures': "Futures",
        'pump': "Pump",
        'dump': "Dump",
        'both': "Both",
        'notify_type': "Notification type",
        'select_exchange': "Select exchange:",
        'select_market': "Select market:",
        'select_timeframe': "Select timeframe:",
        'select_threshold': "Select threshold %:",
        'select_notify_type': "Select notification type:",
        'ai_result': "AI analysis for {}: {}"
    }
}

# === Поддерживаемые биржи, таймфреймы и т.д. ===
SUPPORTED_EXCHANGES = ['Binance', 'Bybit', 'MEXC', 'BingX']
SUPPORTED_TIMEFRAMES = ['30s', '1m', '3m', '5m']
SUPPORTED_THRESHOLDS = [0.5, 1, 2, 3, 5]
SUPPORTED_MARKETS = ['spot', 'futures']
# === Хранилище пользователей ===
user_settings = {}

def get_user_language(user_id):
    return user_settings.get(user_id, {}).get("language", "en")

def translate(user_id, key):
    lang = get_user_language(user_id)
    return translations[lang].get(key, key)

# === Кнопки главного меню ===
def get_main_menu(user_id):
    lang = get_user_language(user_id)
    return ReplyKeyboardMarkup([
        [translations[lang]['language'], translations[lang]['exchange']],
        [translations[lang]['market'], translations[lang]['timeframe']],
        [translations[lang]['threshold'], translations[lang]['notify_type']],
        [translations[lang]['notifications'], translations[lang]['settings']]
    ], resize_keyboard=True)

# === Inline-кнопки для выбора значений ===
def get_inline_keyboard(options, prefix):
    keyboard = [[InlineKeyboardButton(str(opt), callback_data=f"{prefix}:{opt}")]
                for opt in options]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

# === Команда /start ===
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_settings[user_id] = {
        "language": "ru",
        "exchange": "Binance",
        "market": "spot",
        "timeframe": "1m",
        "threshold": 1,
        "notify_type": "both"
    }
    update.message.reply_text("Привет! Я бот мониторинга пампов и дампов.",
                              reply_markup=get_main_menu(user_id))

# === Вывод текущих настроек ===
def show_settings(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    settings = user_settings.get(user_id, {})
    text = "\n".join([
        f"Язык: {settings.get('language', '')}",
        f"Биржа: {settings.get('exchange', '')}",
        f"Рынок: {settings.get('market', '')}",
        f"Таймфрейм: {settings.get('timeframe', '')}",
        f"Порог %: {settings.get('threshold', '')}",
        f"Тип уведомлений: {settings.get('notify_type', '')}"
        
    ])
    update.message.reply_text(text, reply_markup=get_main_menu(user_id))
SUPPORTED_NOTIFY_TYPES = ['pump', 'dump', 'both']
# === Обработка reply-кнопок ===
def handle_reply(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    lang = get_user_language(user_id)

    if text == translations[lang]['language']:
        keyboard = get_inline_keyboard(["ru", "en"], "lang")
        update.message.reply_text("Выберите язык:", reply_markup=keyboard)

    elif text == translations[lang]['exchange']:
        keyboard = get_inline_keyboard(["Binance", "Bybit", "MEXC", "BingX"], "exchange")
        update.message.reply_text("Выберите биржу:", reply_markup=keyboard)

    elif text == translations[lang]['market']:
        keyboard = get_inline_keyboard(["spot", "futures"], "market")
        update.message.reply_text("Выберите рынок:", reply_markup=keyboard)

    elif text == translations[lang]['timeframe']:
        keyboard = get_inline_keyboard(["30s", "1m", "5m", "15m"], "timeframe")
        update.message.reply_text("Выберите таймфрейм:", reply_markup=keyboard)

    elif text == translations[lang]['threshold']:
        keyboard = get_inline_keyboard(["0.5", "1", "2", "5"], "threshold")
        update.message.reply_text("Выберите порог %:", reply_markup=keyboard)

    elif text == translations[lang]['notify_type']:
        keyboard = get_inline_keyboard(["pump", "dump", "both"], "notify")
        update.message.reply_text("Тип уведомлений:", reply_markup=keyboard)

    elif text == translations[lang]['settings']:
        show_settings(update, context)

    else:
        update.message.reply_text("Неизвестная команда.")
        # === CallbackQueryHandler для inline-кнопок ===
def inline_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data
    lang = get_user_language(user_id)

    if data.startswith("lang_"):
        lang_code = data.split("_")[1]
        set_user_setting(user_id, "language", lang_code)
        query.edit_message_text("Язык установлен.")

    elif data.startswith("exchange_"):
        ex = data.split("_")[1]
        set_user_setting(user_id, "exchange", ex)
        query.edit_message_text("Биржа выбрана.")

    elif data.startswith("market_"):
        market = data.split("_")[1]
        set_user_setting(user_id, "market", market)
        query.edit_message_text("Рынок выбран.")

    elif data.startswith("timeframe_"):
        tf = data.split("_")[1]
        set_user_setting(user_id, "timeframe", tf)
        query.edit_message_text("Таймфрейм установлен.")

    elif data.startswith("threshold_"):
        th = float(data.split("_")[1])
        set_user_setting(user_id, "threshold", th)
        query.edit_message_text("Порог установлен.")

    elif data.startswith("notify_"):
        ntype = data.split("_")[1]
        set_user_setting(user_id, "notify_type", ntype)
        query.edit_message_text("Тип уведомлений установлен.")
        # === Обработчик сообщений (ввод текста) ===
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    lang = get_user_language(user_id)

    if text.lower().startswith(("ai ", "аи ")):
        parts = text.split()
        if len(parts) < 2:
            update.message.reply_text("Укажите монету, например: AI BTC")
            return

        symbol = parts[1].upper()
        settings = user_settings.get(user_id, default_settings.copy())
        exchange = settings["exchange"]
        market = settings["market"]
        asyncio.run(ai_analysis(symbol, update, lang, exchange, market))
        return

    if text == get_text(lang, "btn_settings"):
        show_settings(user_id, update, context)
    elif text == get_text(lang, "btn_language"):
        update.message.reply_text(get_text(lang, "choose_lang"), reply_markup=language_markup())
    elif text == get_text(lang, "btn_exchange"):
        update.message.reply_text(get_text(lang, "choose_exchange"), reply_markup=exchange_markup())
    elif text == get_text(lang, "btn_market"):
        update.message.reply_text(get_text(lang, "choose_market"), reply_markup=market_markup())
    elif text == get_text(lang, "btn_timeframe"):
        update.message.reply_text(get_text(lang, "choose_timeframe"), reply_markup=timeframe_markup())
    elif text == get_text(lang, "btn_threshold"):
        update.message.reply_text(get_text(lang, "choose_threshold"), reply_markup=threshold_markup())
    elif text == get_text(lang, "btn_notify_type"):
        update.message.reply_text(get_text(lang, "choose_notify"), reply_markup=notify_type_markup())
    else:
        update.message.reply_text(get_text(lang, "unknown_command"))
        # === Основной webhook endpoint ===
@app.route(f'/{TG_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'OK'

# === Установка webhook ===
@app.route('/')
def index():
    bot.set_webhook(url=f"{APP_URL}/{TG_TOKEN}")
    return 'Webhook установлен!'

# === Регистрация обработчиков ===
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button_handler))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

# === Запуск Flask ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
