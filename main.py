import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
import time
import threading
import random
from flask import Flask
from threading import Thread
import requests

BOT_TOKEN = '7697812728:AAHp1YLSJD5FiqIMSTxKImYSyMkIUply9Xk'

LANGUAGES = {
    'ru': {
        'start': "👋 Привет! Я бот для отслеживания на фьючерсах.\n\nСначала нужно пройти проверку, чтобы подтвердить, что вы не бот.",
        'choose_lang': "🌐 Выберите язык:",
        'choose_exchange': "💱 Выберите биржу:",
        'set_threshold': "✅ Порог установлен: +{percent}% за {seconds} сек.",
        'ask_threshold': "📝 Введите порог и интервал в секундах через пробел. Например: 5 60",
        'alert_pump': "🚀 Рост! Цена выросла на {percent:.2f}% за {seconds} сек. {emoji}",
        'alert_dump': "📉 Падение! Цена упала на {percent:.2f}% за {seconds} сек. {emoji}",
        'menu': "📋 Главное меню",
        'captcha': "🤖 Подтвердите, что вы не бот. Выберите правильный смайл: {target}",
        'captcha_pass': "✅ Проверка пройдена!",
        'captcha_fail': "❌ Неверно. Попробуйте ещё раз.",
        'watching': "🕵️‍♂️ Отслеживаю рынок...",
        'lang_set': "✅ Язык установлен!",
        'exchange_set': "✅ Биржа установлена: {exchange}",
        'interval_set': "✅ Интервал отслеживания установлен: {seconds} сек.",
        'filter_set': "✅ Фильтр отслеживания установлен: {filter}",
        'pump_only': "только пампы",
        'dump_only': "только дампы",
        'all': "все сигналы",
        'suspicious_alert': "⚠️ Подозрительная активность: резкий объём без изменения цены.",
        'captcha_required': "❗️ Сначала нужно пройти проверку (капчу).",
        'btn_language': "🌐 Язык",
        'btn_exchange': "💱 Биржа",
        'btn_interval': "⏳ Интервал",
        'btn_filter': "⚙️ Фильтр",
        'btn_captcha': "🔒 Пройти капчу",
        'btn_captcha_again': "🔒 Пройти капчу заново",
    },
    'en': {
        'start': "👋 Hi! I'm a bot tracking futures markets.\n\nFirst, please verify you are human.",
        'choose_lang': "🌐 Choose your language:",
        'choose_exchange': "💱 Choose exchange:",
        'set_threshold': "✅ Threshold set to +{percent}% every {seconds} seconds.",
        'ask_threshold': "📝 Send threshold and interval in seconds separated by space. Example: 5 60",
        'alert_pump': "🚀 Rise! Price rose {percent:.2f}% in {seconds} sec. {emoji}",
        'alert_dump': "📉 Fall! Price dropped {percent:.2f}% in {seconds} sec. {emoji}",
        'menu': "📋 Main menu",
        'captcha': "🤖 Please verify you are human. Tap the emoji: {target}",
        'captcha_pass': "✅ Verified!",
        'captcha_fail': "❌ Wrong emoji. Try again.",
        'watching': "🕵️‍♂️ Watching the market...",
        'lang_set': "✅ Language set!",
        'exchange_set': "✅ Exchange set to {exchange}",
        'interval_set': "✅ Tracking interval set to {seconds} seconds.",
        'filter_set': "✅ Tracking filter set to {filter}",
        'pump_only': "only pumps",
        'dump_only': "only dumps",
        'all': "all signals",
        'suspicious_alert': "⚠️ Suspicious activity: sudden volume spike without price change.",
        'captcha_required': "❗️ You must pass captcha first.",
        'btn_language': "🌐 Language",
        'btn_exchange': "💱 Exchange",
        'btn_interval': "⏳ Interval",
        'btn_filter': "⚙️ Filter",
        'btn_captcha': "🔒 Pass captcha",
        'btn_captcha_again': "🔒 Pass captcha again",
    }
}

user_settings = {}

def get_lang(chat_id):
    return user_settings.get(chat_id, {}).get('lang', 'ru')

def t(chat_id, key, **kwargs):
    lang = get_lang(chat_id)
    text = LANGUAGES.get(lang, LANGUAGES['ru']).get(key, key)
    return text.format(**kwargs)

def main_menu_keyboard(chat_id):
    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t(chat_id, 'btn_captcha'), callback_data='start_captcha')]
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(chat_id, 'btn_language'), callback_data='show_language')],
        [InlineKeyboardButton(t(chat_id, 'btn_exchange'), callback_data='show_exchange')],
        [InlineKeyboardButton(t(chat_id, 'btn_interval'), callback_data='show_interval')],
        [InlineKeyboardButton(t(chat_id, 'btn_filter'), callback_data='show_filter')],
        [InlineKeyboardButton(t(chat_id, 'btn_captcha_again'), callback_data='start_captcha')]
    ])

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
    ])

def exchange_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 MEXC", callback_data='exchange_mex')],
        [InlineKeyboardButton("💹 Binance", callback_data='exchange_bin')],
        [InlineKeyboardButton("📈 KuCoin", callback_data='exchange_ku')],
        [InlineKeyboardButton("📉 ByBit", callback_data='exchange_by')],
        [InlineKeyboardButton("💰 BingX", callback_data='exchange_bing')],
    ])

def interval_keyboard(chat_id):
    # Варианты интервалов с надписями на языке пользователя
    intervals = [
        (30, "30 сек", "30 sec"),
        (60, "60 сек", "60 sec"),
        (120, "120 сек", "120 sec"),
        (300, "300 сек", "300 sec")
    ]
    buttons = []
    lang = get_lang(chat_id)
    for sec, ru_label, en_label in intervals:
        label = ru_label if lang == 'ru' else en_label
        buttons.append([InlineKeyboardButton(label, callback_data=f'interval_{sec}')])
    return InlineKeyboardMarkup(buttons)

def filter_keyboard(chat_id):
    lang = get_lang(chat_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(chat_id, 'pump_only'), callback_data='filter_pump')],
        [InlineKeyboardButton(t(chat_id, 'dump_only'), callback_data='filter_dump')],
        [InlineKeyboardButton(t(chat_id, 'all'), callback_data='filter_all')],
    ])

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {
        'lang': 'ru',
        'exchange': 'mex',
        'threshold': 5.0,
        'interval': 60,
        'last_notify': 0,
        'filter': 'all',
        'captcha_passed': False,
    }
    update.message.reply_text(t(chat_id, 'start'), reply_markup=main_menu_keyboard(chat_id))

def text_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        update.message.reply_text(t(chat_id, 'captcha_required'), reply_markup=main_menu_keyboard(chat_id))
        return

    if text == "/start":
        start(update, context)
    elif text == "/menu":
        update.message.reply_text(t(chat_id, 'menu'), reply_markup=main_menu_keyboard(chat_id))
    else:
        update.message.reply_text(t(chat_id, 'menu'), reply_markup=main_menu_keyboard(chat_id))

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data

    if data == 'start_captcha':
        emoji_captcha(update, context)
        return

    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        query.answer(text=t(chat_id, 'captcha_required'))
        return

    if data == 'show_language':
        query.edit_message_text(t(chat_id, 'choose_lang'), reply_markup=language_keyboard())
    elif data == 'show_exchange':
        query.edit_message_text(t(chat_id, 'choose_exchange'), reply_markup=exchange_keyboard())
    elif data == 'show_interval':
        query.edit_message_text(t(chat_id, 'ask_threshold'), reply_markup=interval_keyboard(chat_id))
    elif data == 'show_filter':
        query.edit_message_text(t(chat_id, 'menu'), reply_markup=filter_keyboard(chat_id))

    elif data.startswith('lang_'):
        lang_code = data.split('_')[1]
        user_settings.setdefault(chat_id, {})['lang'] = lang_code
        # После смены языка обновляем меню на новом языке
        query.edit_message_text(t(chat_id, 'lang_set'), reply_markup=main_menu_keyboard(chat_id))

    elif data.startswith('exchange_'):
        exch_code = data.split('_')[1]
        user_settings.setdefault(chat_id, {})['exchange'] = exch_code
        query.edit_message_text(t(chat_id, 'exchange_set', exchange=exch_code.upper()), reply_markup=main_menu_keyboard(chat_id))

    elif data.startswith('interval_'):
        sec = int(data.split('_')[1])
        user_settings.setdefault(chat_id, {})['interval'] = sec
        query.edit_message_text(t(chat_id, 'interval_set', seconds=sec), reply_markup=main_menu_keyboard(chat_id))

    elif data.startswith('filter_'):
        filt = data.split('_')[1]
        if filt in ('pump', 'dump', 'all'):
            user_settings.setdefault(chat_id, {})['filter'] = filt
            filter_name = t(chat_id, filt + '_only') if filt != 'all' else t(chat_id, 'all')
            query.edit_message_text(t(chat_id, 'filter_set', filter=filter_name), reply_markup=main_menu_keyboard(chat_id))

    elif data.startswith('captcha_'):
        handle_captcha(update, context)

def emoji_captcha(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊"]
    target = random.choice(emojis)
    options = random.sample(emojis, 4)
    if target not in options:
        options[0] = target
    random.shuffle(options)
    buttons = []
    for idx, emoji in enumerate(options):
        buttons.append([InlineKeyboardButton(emoji, callback_data=f'captcha_{idx}')])
    context.user_data['captcha_target_emoji'] = target
    context.user_data['captcha_options'] = options
    # Отправляем сообщение с кнопками эмоджи капчи
    if update.callback_query:
        update.callback_query.edit_message_text(
            t(chat_id, 'captcha', target=target),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        update.message.reply_text(
            t(chat_id, 'captcha', target=target),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

def handle_captcha(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    selected_idx = int(query.data.replace('captcha_', ''))
    options = context.user_data.get('captcha_options', [])
    target_emoji = context.user_data.get('captcha_target_emoji')

    if options and 0 <= selected_idx < len(options):
        selected_emoji = options[selected_idx]
        if selected_emoji == target_emoji:
            if chat_id not in user_settings:
                user_settings[chat_id] = {}
            user_settings[chat_id]['captcha_passed'] = True
            query.edit_message_text(t(chat_id, 'captcha_pass'), reply_markup=main_menu_keyboard(chat_id))
        else:
            query.edit_message_text(t(chat_id, 'captcha_fail'), reply_markup=None)
            # Немного задержки, потом новая капча
            time.sleep(1)
            emoji_captcha(update, context)
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'), reply_markup=None)
        time.sleep(1)
        emoji_captcha(update, context)

# Функция проверки подозрительных объёмов
def check_suspicious_volume(current_volume, avg_volume, threshold=3.0):
    if avg_volume == 0:
        return False
    return current_volume >= avg_volume * threshold

volume_history = {}

def monitor_loop():
    while True:
        for chat_id, settings in user_settings.items():
            if not settings.get('captcha_passed', False):
                continue

            exchange = settings.get('exchange', 'mex')
            threshold = settings.get('threshold', 5.0)
            interval = settings.get('interval', 60)
            last_notify = settings.get('last_notify', 0)
            filter_type = settings.get('filter', 'all')
            now = time.time()

            if now - last_notify < interval:
                continue

            try:
                data = []
                if exchange == 'mex':
                    url = 'https://contract.mexc.com/api/v1/contract/ticker'
                    resp = requests.get(url, timeout=10).json()
                    data = resp.get('data', [])
                elif exchange == 'bin':
                    url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
                    data = requests.get(url, timeout=10).json()
                    # Фильтруем фьючерсы
                    data = [coin for coin in data if coin['symbol'].endswith('USDT') or coin['symbol'].endswith('PERP')]
                elif exchange == 'ku':
                    url = 'https://api-futures.kucoin.com/api/v1/contract/ticker'
                    resp = requests.get(url, timeout=10).json()
                    data = resp.get('data', {}).get('ticker', [])
                elif exchange == 'by':
                    url = 'https://api.bybit.com/v2/public/tickers'
                    resp = requests.get(url, timeout=10).json()
                    data = resp.get('result', [])
                elif exchange == 'bing':
                    url = 'https://api.bingx.com/api/v1/contract/ticker'
                    resp = requests.get(url, timeout=10).json()
                    data = resp.get('data', [])
                else:
                    data = []

                for coin in data:
                    symbol = coin.get('symbol') or coin.get('contractCode') or coin.get('symbolName') or coin.get('name')
                    if not symbol:
                        continue
