import logging
import time
import json
import requests
from flask import Flask, request
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
import threading

# === Настройки ===
TOKEN = '7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE'
URL = 'https://btm-c4tt.onrender.com'

LANGUAGES = ['EN', 'RU']
EXCHANGES = ['Binance', 'Bybit', 'MEXC', 'BingX']
MARKETS = ['Spot', 'Futures']
NOTIFY_TYPES = ['Pump', 'Dump', 'Both']
TIMEFRAMES = ['30s', '1m', '3m', '5m']
PERCENT_THRESHOLDS = ['1%', '2%', '3%', '5%', '10%']

user_data = {}  # {user_id: {settings}}

# === Локализация ===
TEXTS = {
    'EN': {
        'start': "✅ Please verify CAPTCHA to continue.",
        'verified': "✅ Verified! Choose an option below:",
        'language_set': "✅ Language set to English.",
        'menu': "🔧 Main Menu:",
        'select_exchange': "📈 Select exchange:",
        'select_market': "💹 Select market:",
        'select_notify_type': "🔔 Select notification type:",
        'select_timeframe': "⏱ Select timeframe:",
        'select_threshold': "📊 Select % threshold:",
        'your_settings': "⚙️ Your settings:",
        'settings_saved': "✅ Settings saved.",
        'alert': "🚨 {symbol} changed by {percent}% on {exchange} ({market})"
    },
    'RU': {
        'start': "✅ Подтвердите CAPTCHA, чтобы продолжить.",
        'verified': "✅ Верификация пройдена! Выберите опцию ниже:",
        'language_set': "✅ Язык установлен: Русский.",
        'menu': "🔧 Главное меню:",
        'select_exchange': "📈 Выберите биржу:",
        'select_market': "💹 Выберите рынок:",
        'select_notify_type': "🔔 Тип уведомлений:",
        'select_timeframe': "⏱ Выберите таймфрейм:",
        'select_threshold': "📊 Порог изменения в %:",
        'your_settings': "⚙️ Ваши настройки:",
        'settings_saved': "✅ Настройки сохранены.",
        'alert': "🚨 {symbol} изменился на {percent}% на {exchange} ({market})"
    }
}

# === Flask ===
app = Flask(__name__)

@app.route('/')
def index():
    return 'Bot is running.'

# === Telegram ===
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = user_data.get(user_id, {}).get('language', 'EN')
    user_data[user_id] = {
        'verified': True,
        'language': lang,
        'exchange': 'Binance',
        'market': 'Spot',
        'notify_type': 'Both',
        'threshold': 3,
        'timeframe': '1m'
    }
    reply_menu(update, context)

def reply_menu(update, context):
    user_id = update.effective_user.id
    lang = user_data[user_id]['language']
    markup = ReplyKeyboardMarkup(
        [
            [KeyboardButton('🌐 Language'), KeyboardButton('📈 Exchange')],
            [KeyboardButton('💹 Market'), KeyboardButton('🔔 Notify type')],
            [KeyboardButton('⏱ Timeframe'), KeyboardButton('📊 Threshold')],
            [KeyboardButton('⚙️ My settings')]
        ],
        resize_keyboard=True
    )
    update.message.reply_text(TEXTS[lang]['menu'], reply_markup=markup)

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text
    lang = user_data.get(user_id, {}).get('language', 'EN')

    if message == '🌐 Language':
        lang_markup = ReplyKeyboardMarkup(
            [[KeyboardButton("English")], [KeyboardButton("Русский")]],
            resize_keyboard=True
        )
        update.message.reply_text("🌐 Select language:", reply_markup=lang_markup)
    elif message in ['English', 'Русский']:
        new_lang = 'EN' if message == 'English' else 'RU'
        user_data[user_id]['language'] = new_lang
        update.message.reply_text(TEXTS[new_lang]['language_set'])
        reply_menu(update, context)
    elif message == '📈 Exchange':
        exch_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(e)] for e in EXCHANGES],
            resize_keyboard=True
        )
        update.message.reply_text(TEXTS[lang]['select_exchange'], reply_markup=exch_markup)
    elif message in EXCHANGES:
        user_data[user_id]['exchange'] = message
        update.message.reply_text(TEXTS[lang]['settings_saved'])
        reply_menu(update, context)
    elif message == '💹 Market':
        m_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(m)] for m in MARKETS],
            resize_keyboard=True
        )
        update.message.reply_text(TEXTS[lang]['select_market'], reply_markup=m_markup)
    elif message in MARKETS:
        user_data[user_id]['market'] = message
        update.message.reply_text(TEXTS[lang]['settings_saved'])
        reply_menu(update, context)
    elif message == '🔔 Notify type':
        n_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(n)] for n in NOTIFY_TYPES],
            resize_keyboard=True
        )
        update.message.reply_text(TEXTS[lang]['select_notify_type'], reply_markup=n_markup)
    elif message in NOTIFY_TYPES:
        user_data[user_id]['notify_type'] = message
        update.message.reply_text(TEXTS[lang]['settings_saved'])
        reply_menu(update, context)
    elif message == '⏱ Timeframe':
        tf_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(t)] for t in TIMEFRAMES],
            resize_keyboard=True
        )
        update.message.reply_text(TEXTS[lang]['select_timeframe'], reply_markup=tf_markup)
    elif message in TIMEFRAMES:
        user_data[user_id]['timeframe'] = message
        update.message.reply_text(TEXTS[lang]['settings_saved'])
        reply_menu(update, context)
    elif message == '📊 Threshold':
        th_markup = ReplyKeyboardMarkup(
            [[KeyboardButton(p)] for p in PERCENT_THRESHOLDS],
            resize_keyboard=True
        )
        update.message.reply_text(TEXTS[lang]['select_threshold'], reply_markup=th_markup)
    elif message in PERCENT_THRESHOLDS:
        user_data[user_id]['threshold'] = int(message.replace('%', ''))
        update.message.reply_text(TEXTS[lang]['settings_saved'])
        reply_menu(update, context)
    elif message == '⚙️ My settings':
        u = user_data[user_id]
        settings_text = f"{TEXTS[lang]['your_settings']}

"                         f"🌐 Language: {u['language']}
"                         f"📈 Exchange: {u['exchange']}
"                         f"💹 Market: {u['market']}
"                         f"🔔 Type: {u['notify_type']}
"                         f"⏱ Timeframe: {u['timeframe']}
"                         f"📊 Threshold: {u['threshold']}%"
        update.message.reply_text(settings_text)
    else:
        update.message.reply_text(TEXTS[lang]['menu'])

# === Уведомления ===

def monitor_prices():
    while True:
        for user_id, settings in user_data.items():
            if not settings.get('verified'):
                continue
            exchange = settings['exchange']
            # Здесь реальная логика API запросов к биржам
            # Пример: символ вырос более чем на threshold
            symbol = 'BTCUSDT'
            percent = settings['threshold'] + 1
            lang = settings['language']
            alert = TEXTS[lang]['alert'].format(
                symbol=symbol,
                percent=percent,
                exchange=exchange,
                market=settings['market']
            )
            try:
                context = updater.dispatcher.bot
                context.send_message(chat_id=user_id, text=alert)
            except Exception as e:
                print(f"Error sending to {user_id}: {e}")
        time.sleep(60)

# === Запуск ===

updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Отдельный поток для мониторинга
monitor_thread = threading.Thread(target=monitor_prices, daemon=True)
monitor_thread.start()

updater.start_polling()
app.run(host="0.0.0.0", port=8080)
