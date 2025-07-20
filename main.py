import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
import time
import threading
import random
import requests

# ========== CONFIG ==========

BOT_TOKEN = '7697812728:AAHp1YLSJD5FiqIMSTxKImYSyMkIUply9Xk'  # <-- вставь свой токен здесь

# ========== ЛОГГИРОВАНИЕ ==========

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== ЯЗЫКИ ==========

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

# ========== ПЕРЕМЕННЫЕ ==========

user_settings = {}
volume_history = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_lang(chat_id):
    return user_settings.get(chat_id, {}).get('lang', 'ru')

def t(chat_id, key, **kwargs):
    lang = get_lang(chat_id)
    text = LANGUAGES.get(lang, LANGUAGES['ru']).get(key, key)
    if key not in LANGUAGES.get(lang, {}):
        logging.warning(f"Missing translation: {key} in {lang}")
    return text.format(**kwargs)

def check_suspicious_volume(current_volume, avg_volume, threshold=3.0):
    if avg_volume == 0:
        return False
    return current_volume >= avg_volume * threshold

# ========== ОБРАБОТЧИКИ ==========

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
    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        update.message.reply_text(t(chat_id, 'captcha_required'), reply_markup=main_menu_keyboard(chat_id))
        return
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
        user_settings.setdefault(chat_id, {})['filter'] = filt
        label = t(chat_id, f'{filt}_only') if filt in ['pump', 'dump'] else t(chat_id, 'all')
        query.edit_message_text(t(chat_id, 'filter_set', filter=label), reply_markup=main_menu_keyboard(chat_id))

    elif data.startswith('captcha_'):
        handle_captcha(update, context)

# ========== КЛАВИАТУРЫ ==========

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
        [InlineKeyboardButton(t(chat_id, 'btn_captcha_again'), callback_data='start_captcha')],
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
    intervals = [(30, "30 сек", "30 sec"), (60, "60 сек", "60 sec"), (120, "120 сек", "120 sec"), (300, "300 сек", "300 sec")]
    lang = get_lang(chat_id)
    buttons = [[InlineKeyboardButton(ru if lang == 'ru' else en, callback_data=f'interval_{sec}')] for sec, ru, en in intervals]
    return InlineKeyboardMarkup(buttons)

def filter_keyboard(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(chat_id, 'pump_only'), callback_data='filter_pump')],
        [InlineKeyboardButton(t(chat_id, 'dump_only'), callback_data='filter_dump')],
        [InlineKeyboardButton(t(chat_id, 'all'), callback_data='filter_all')],
    ])

# ========== CAPTCHA ==========

def emoji_captcha(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    emojis = ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊"]
    target = random.choice(emojis)
    options = random.sample(emojis, 4)
    if target not in options:
        options[0] = target
    random.shuffle(options)

    buttons = [[InlineKeyboardButton(emoji, callback_data=f'captcha_{i}')] for i, emoji in enumerate(options)]
    context.user_data['captcha_target_emoji'] = target
    context.user_data['captcha_options'] = options

    msg = t(chat_id, 'captcha', target=target)
    if update.callback_query:
        update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

def handle_captcha(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    selected_idx = int(query.data.replace('captcha_', ''))
    options = context.user_data.get('captcha_options', [])
    target = context.user_data.get('captcha_target_emoji')

    if 0 <= selected_idx < len(options) and options[selected_idx] == target:
        user_settings.setdefault(chat_id, {})['captcha_passed'] = True
        query.edit_message_text(t(chat_id, 'captcha_pass'), reply_markup=main_menu_keyboard(chat_id))
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'))
        emoji_captcha(update, context)

# ========== МОНИТОРИНГ РЫНКА ==========

def monitor_loop(bot):
    while True:
        time.sleep(3)  # чтобы не спамить API

        for chat_id, settings in user_settings.items():
            if not settings.get('captcha_passed'):
                continue

            try:
                exchange = settings.get('exchange', 'mex')
                threshold = settings.get('threshold', 5.0)
                interval = settings.get('interval', 60)
                last_notify = settings.get('last_notify', 0)
                filter_type = settings.get('filter', 'all')
                now = time.time()

                if now - last_notify < interval:
                    continue

                url = ''
                data = []

                if exchange == 'mex':
                    url = 'https://contract.mexc.com/api/v1/contract/ticker'
                    data = requests.get(url, timeout=10).json().get('data', [])
                elif exchange == 'bin':
                    url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
                    data = [d for d in requests.get(url, timeout=10).json() if d['symbol'].endswith('USDT')]
                elif exchange == 'ku':
                    url = 'https://api-futures.kucoin.com/api/v1/contract/ticker'
                    data = requests.get(url, timeout=10).json().get('data', {}).get('ticker', [])
                elif exchange == 'by':
                    url = 'https://api.bybit.com/v2/public/tickers'
                    data = requests.get(url, timeout=10).json().get('result', [])
                elif exchange == 'bing':
                    url = 'https://api.bingx.com/api/v1/contract/ticker'
                    data = requests.get(url, timeout=10).json().get('data', [])

                for coin in data:
                    symbol = coin.get('symbol') or coin.get('contractCode') or coin.get('symbolName') or coin.get('name')
                    if not symbol:
                        continue

                    try:
                        price = float(coin.get('lastPrice') or coin.get('lastDealPrice') or 0)
                        open_price = float(coin.get('openPrice') or coin.get('prevPrice24h') or 0)
                        volume = float(coin.get('volume') or 0)
                    except:
                        continue

                    if open_price == 0:
                        continue

                    change_percent = ((price - open_price) / open_price) * 100

                    # Подозрительная активность
                    avg_vol = volume_history.get(symbol, 0)
                    if check_suspicious_volume(volume, avg_vol):
                        bot.send_message(chat_id=chat_id, text=t(chat_id, 'suspicious_alert'))

                    if abs(change_percent) >= threshold:
                        if (change_percent > 0 and filter_type == 'dump') or (change_percent < 0 and filter_type == 'pump'):
                            continue
                        key = 'alert_pump' if change_percent > 0 else 'alert_dump'
                        emoji = "🚀" if change_percent > 0 else "📉"
                        bot.send_message(chat_id=chat_id, text=t(chat_id, key, percent=change_percent, seconds=interval, emoji=emoji))
                        user_settings[chat_id]['last_notify'] = now

                    volume_history[symbol] = (volume_history.get(symbol, 0) * 0.9) + (volume * 0.1)

            except Exception as e:
                logging.error(f"Monitor error: {e}")

# ========== ЗАПУСК ==========

updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
dp.add_handler(CallbackQueryHandler(button_handler))

threading.Thread(target=monitor_loop, args=(updater.bot,), daemon=True).start()

updater.start_polling()
updater.idle()
