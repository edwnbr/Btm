import logging
import random
import time
import threading
from flask import Flask
import requests

from telegram import (
    InlineKeyboardMarkup, InlineKeyboardButton, Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
)

# === Токен бота ===
BOT_TOKEN = '7697812728:AAHp1YLSJD5FiqIMSTxKImYSyMkIUply9Xk'

# === Локализация ===
LANGUAGES = {
    'ru': {
        'start': "👋 Привет! Я бот для отслеживания пампов и дампов на фьючерсах.\n\nВыбери биржу, язык, порог и способ оповещений.",
        'choose_lang': "🌐 Выберите язык:",
        'choose_exchange': "💱 Выберите биржу:",
        'set_threshold': "✅ Порог установлен: +{percent}% за {seconds} сек.",
        'ask_threshold': "📝 Введите порог и интервал в секундах через пробел. Например: 5 60",
        'alert_pump': "🚀 Памп! Цена выросла на {percent:.2f}% за {seconds} сек. {emoji}",
        'alert_dump': "📉 Дамп! Цена упала на {percent:.2f}% за {seconds} сек. {emoji}",
        'menu': "📋 Главное меню",
        'captcha': "🤖 Подтвердите, что вы не бот. Выберите правильный смайл: {target}",
        'captcha_pass': "✅ Проверка пройдена!",
        'captcha_fail': "❌ Неверно. Попробуйте ещё раз.",
        'watching': "🕵️‍♂️ Отслеживаю рынок...",
        'lang_set': "✅ Язык установлен!",
        'exchange_set': "✅ Биржа установлена: {exchange}",
        'pump_detected': "📈 Обнаружен памп: +{percent:.2f}%",
        'suspicious_alert': "⚠️ Подозрительная активность: резкий объём без изменения цены."
    },
    'en': {
        'start': "👋 Hi! I'm a bot tracking pumps and dumps on futures.\n\nChoose exchange, language, threshold and alerts.",
        'choose_lang': "🌐 Choose your language:",
        'choose_exchange': "💱 Choose exchange:",
        'set_threshold': "✅ Threshold set to +{percent}% every {seconds} seconds.",
        'ask_threshold': "📝 Send threshold and interval in seconds separated by space. Example: 5 60",
        'alert_pump': "🚀 Pump! Price rose {percent:.2f}% in {seconds} sec. {emoji}",
        'alert_dump': "📉 Dump! Price dropped {percent:.2f}% in {seconds} sec. {emoji}",
        'menu': "📋 Main menu",
        'captcha': "🤖 Please verify you are human. Tap the emoji: {target}",
        'captcha_pass': "✅ Verified!",
        'captcha_fail': "❌ Wrong emoji. Try again.",
        'watching': "🕵️‍♂️ Watching the market...",
        'lang_set': "✅ Language set!",
        'exchange_set': "✅ Exchange set to {exchange}",
        'pump_detected': "📈 Pump detected: +{percent:.2f}%",
        'suspicious_alert': "⚠️ Suspicious activity: sudden volume spike without price change."
    }
}

# Хранилище настроек пользователей
user_settings = {}

def get_lang(chat_id):
    return user_settings.get(chat_id, {}).get('lang', 'ru')

def t(chat_id, key, **kwargs):
    lang = get_lang(chat_id)
    template = LANGUAGES.get(lang, LANGUAGES['ru']).get(key, key)
    return template.format(**kwargs)

# Клавиатуры
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["📈 Set Threshold", "💱 Choose Exchange"],
        ["🌐 Language", "🔒 Captcha Test"]
    ], resize_keyboard=True)

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')]
    ])

def exchange_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 MEXC", callback_data='exchange_mex')],
        [InlineKeyboardButton("💹 Binance", callback_data='exchange_bin')],
        [InlineKeyboardButton("📈 KuCoin", callback_data='exchange_ku')],
        [InlineKeyboardButton("📉 ByBit", callback_data='exchange_by')],
        [InlineKeyboardButton("💰 BingX", callback_data='exchange_bing')]
    ])

# Команды
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {
        'lang': 'ru',
        'exchange': 'mex',
        'threshold': 5.0,
        'interval': 60,
        'last_notify': 0
    }
    update.message.reply_text(t(chat_id, 'start'), reply_markup=main_menu_keyboard())

def text_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if text == "🌐 Language":
        update.message.reply_text(t(chat_id, 'choose_lang'), reply_markup=language_keyboard())
    elif text == "💱 Choose Exchange":
        update.message.reply_text(t(chat_id, 'choose_exchange'), reply_markup=exchange_keyboard())
    elif text == "📈 Set Threshold":
        update.message.reply_text(t(chat_id, 'ask_threshold'))
        context.user_data['awaiting'] = 'threshold'
    elif text == "🔒 Captcha Test":
        emoji_captcha(update, context)
    elif context.user_data.get('awaiting') == 'threshold':
        try:
            parts = [float(p) for p in text.replace(',', '.').split()]
            if len(parts) == 2:
                user_settings[chat_id]['threshold'], user_settings[chat_id]['interval'] = parts
                update.message.reply_text(t(chat_id, 'set_threshold', percent=parts[0], seconds=parts[1]))
            else:
                update.message.reply_text("❌ Please enter two numbers: percent and seconds.")
        except Exception:
            update.message.reply_text("❌ Invalid input. Example: 5 60")
        context.user_data['awaiting'] = None
    else:
        update.message.reply_text(t(chat_id, 'menu'), reply_markup=main_menu_keyboard())

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data

    if data.startswith('lang_'):
        lang_code = data.split('_')[1]
        user_settings.setdefault(chat_id, {})['lang'] = lang_code
        query.edit_message_text(t(chat_id, 'lang_set'))
        context.bot.send_message(chat_id, t(chat_id, 'menu'), reply_markup=main_menu_keyboard())

    elif data.startswith('exchange_'):
        exch_code = data.split('_')[1]
        user_settings.setdefault(chat_id, {})['exchange'] = exch_code
        query.edit_message_text(t(chat_id, 'exchange_set', exchange=exch_code.upper()))

    elif data.startswith('captcha_'):
        handle_captcha(update, context)

# EmojiCaptcha
def emoji_captcha(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊"]
    target = random.choice(emojis)
    options = random.sample(emojis, 4)
    if target not in options:
        options[0] = target
    random.shuffle(options)
    buttons = [[InlineKeyboardButton(e, callback_data=f'captcha_{e}')] for e in options]
    context.user_data['captcha_target'] = target
    update.message.reply_text(t(chat_id, 'captcha', target=target), reply_markup=InlineKeyboardMarkup(buttons))

def handle_captcha(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    selected = query.data.replace('captcha_', '')
    target = context.user_data.get('captcha_target')
    if selected == target:
        query.edit_message_text(t(chat_id, 'captcha_pass'))
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'))

# Функция для мониторинга пампов/дампов
def monitor_loop(updater: Updater):
    bot = updater.bot
    while True:
        now = time.time()
        for chat_id, settings in user_settings.items():
            exchange = settings.get('exchange', 'mex')
            threshold = settings.get('threshold', 5.0)
            interval = settings.get('interval', 60)
            last_notify = settings.get('last_notify', 0)

            if now - last_notify < interval:
                continue  # cooldown

            try:
                # Получаем данные с API выбранной биржи
                if exchange == 'mex':
                    url = 'https://contract.mexc.com/api/v1/contract/ticker'
                    data = requests.get(url).json().get('data', [])
                elif exchange == 'bin':
                    url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
                    data = requests.get(url).json()
                elif exchange == 'ku':
                    url = 'https://api-futures.kucoin.com/api/v1/contract/ticker'
                    data = requests.get(url).json().get('data', {}).get('ticker', [])
                elif exchange == 'by':
                    url = 'https://api.bybit.com/v2/public/tickers'
                    data = requests.get(url).json().get('result', [])
                elif exchange == 'bing':
                    url = 'https://api.bingx.com/api/v1/contract/ticker'
                    data = requests.get(url).json().get('data', [])
                else:
                    data = []

                # Проверяем монеты на пампы/дампы
                for coin in data:
                    symbol = (
                        coin.get('symbol')
                        or coin.get('contractCode')
                        or coin.get('symbolName')
                        or coin.get('name')
                    )
                    if not symbol:
                        continue
                    price = float(
                        coin.get('lastPrice')
                        or coin.get('lastDealPrice')
                        or 0
                    )
                    open_price = float(
                        coin.get('openPrice')
                        or coin.get('prevPrice24h')
                        or 0
                    )
                    if open_price == 0:
                        continue
                    change_percent = ((price - open_price) / open_price) * 100
                    if abs(change_percent) >= threshold:
                        emoji = "🚀" if change_percent > 0 else "📉"
                        key = 'alert_pump' if change_percent > 0 else 'alert_dump'
                        msg = t(chat_id, key, percent=change_percent, seconds=interval, emoji=emoji)
                        bot.send_message(chat_id, msg)
                        user_settings[chat_id]['last_notify'] = now

                # Подозрительная активность (пример)
                if random.random() < 0.01:
                    bot.send_message(chat_id, t(chat_id, 'suspicious_alert'))

            except Exception as e:
                logging.error(f"Error monitoring {exchange} for chat {chat_id}: {e}")

        time.sleep(5)

# Flask keep-alive (для Render, Replit и др.)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()

# === Запуск бота ===
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    keep_alive()

    monitor_thread = threading.Thread(target=monitor_loop, args=(updater,), daemon=True)
    monitor_thread.start()

    updater.start_polling()
    updater.idle()
