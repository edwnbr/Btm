import os
import time
import json
import logging
import random
import threading
import requests
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackContext,
    MessageHandler, Filters, CallbackQueryHandler
)

# ===================== CONFIG =====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = 8443
SETTINGS_FILE = "user_settings.json"

logging.basicConfig(level=logging.INFO)
user_settings = {}
volume_history = {}

# ===================== LOCALIZATION =====================
LANGUAGES = {
    'en': {
        'start': "👋 Welcome! Please verify you are human.",
        'captcha': "🤖 Tap the emoji: {target}",
        'captcha_pass': "✅ Verified!",
        'captcha_fail': "❌ Wrong emoji. Try again.",
        'captcha_required': "❗️ Please complete the captcha first.",
        'alert_pump': "🚀 Price up {percent:.2f}% in {seconds}s {emoji}",
        'alert_dump': "📉 Price down {percent:.2f}% in {seconds}s {emoji}",
        'suspicious_alert': "⚠️ Suspicious volume spike detected!",
        'menu_settings': "⚙️ Settings",
        'menu_exchange': "📈 Exchange",
        'menu_language': "🌐 Language",
        'menu_interval': "⏱ Interval",
        'menu_threshold': "📉 Threshold (%)",
        'menu_market': "💹 Market",
        'menu_direction': "📊 Alerts",
        'back': "🔙 Back",
        'intervals': ["30s", "60s", "120s"],
        'markets': ["Futures", "Spot"],
        'directions': ["Pump only", "Dump only", "Both"],
        'languages': ["English", "Русский"],
    },
    'ru': {
        'start': "👋 Добро пожаловать! Пожалуйста, подтвердите, что вы человек.",
        'captcha': "🤖 Нажмите на смайлик: {target}",
        'captcha_pass': "✅ Проверка пройдена!",
        'captcha_fail': "❌ Неверный смайлик. Попробуйте снова.",
        'captcha_required': "❗️ Пожалуйста, сначала пройдите капчу.",
        'alert_pump': "🚀 Цена выросла на {percent:.2f}% за {seconds} сек. {emoji}",
        'alert_dump': "📉 Цена упала на {percent:.2f}% за {seconds} сек. {emoji}",
        'suspicious_alert': "⚠️ Обнаружен подозрительный всплеск объема!",
        'menu_settings': "⚙️ Настройки",
        'menu_exchange': "📈 Биржа",
        'menu_language': "🌐 Язык",
        'menu_interval': "⏱ Интервал",
        'menu_threshold': "📉 Порог (%)",
        'menu_market': "💹 Рынок",
        'menu_direction': "📊 Уведомления",
        'back': "🔙 Назад",
        'intervals': ["30с", "60с", "120с"],
        'markets': ["Фьючерсы", "Спот"],
        'directions': ["Только рост", "Только падение", "Оба"],
        'languages': ["English", "Русский"],
    }
}

def t(chat_id, key, **kwargs):
    lang = user_settings.get(chat_id, {}).get('lang', 'en')
    return LANGUAGES.get(lang, LANGUAGES['en']).get(key, key).format(**kwargs)
    # ===================== CAPTCHA =====================
def emoji_captcha(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    emojis = ["🐶", "🐱", "🐭", "🐰", "🦊"]
    target = random.choice(emojis)
    options = random.sample(emojis, 4)
    if target not in options:
        options[0] = target
    random.shuffle(options)

    context.user_data['captcha_target_emoji'] = target
    context.user_data['captcha_options'] = options

    buttons = [[InlineKeyboardButton(e, callback_data=f'captcha_{i}')] for i, e in enumerate(options)]
    msg = t(chat_id, 'captcha', target=target)

    if update.callback_query:
        update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

def handle_captcha(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    idx = int(query.data.replace('captcha_', ''))
    options = context.user_data.get('captcha_options', [])
    target = context.user_data.get('captcha_target_emoji')

    if 0 <= idx < len(options) and options[idx] == target:
        user_settings.setdefault(chat_id, {})['captcha_passed'] = True
        query.edit_message_text(t(chat_id, 'captcha_pass'))
        save_settings()
        show_main_menu(update, context)
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'))
        emoji_captcha(update, context)

# ===================== SETTINGS =====================
def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(user_settings, f)

def load_settings():
    global user_settings
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            user_settings = json.load(f)

# ===================== MAIN MENU =====================
def show_main_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = user_settings.get(chat_id, {}).get('lang', 'en')
    L = LANGUAGES[lang]
    buttons = [
        [InlineKeyboardButton(L['menu_settings'], callback_data="menu_settings")]
    ]
    if update.callback_query:
        update.callback_query.edit_message_text("✅", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.message.reply_text("✅", reply_markup=InlineKeyboardMarkup(buttons))

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {
        'lang': 'en',
        'exchange': 'binance',
        'threshold': 5.0,
        'interval': 60,
        'market': 'futures',
        'direction': 'both',
        'captcha_passed': False,
        'last_notify': 0,
    }
    save_settings()
    update.message.reply_text(t(chat_id, 'start'))
    emoji_captcha(update, context)
    # ===================== SETTINGS MENU =====================
EXCHANGES = ['binance', 'bybit', 'mexc', 'bingx', 'kucoin', 'okx']

def settings_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = user_settings.get(chat_id, {}).get('lang', 'en')
    L = LANGUAGES[lang]

    buttons = [
        [InlineKeyboardButton(L['menu_language'], callback_data="set_lang")],
        [InlineKeyboardButton(L['menu_exchange'], callback_data="set_exchange")],
        [InlineKeyboardButton(L['menu_market'], callback_data="set_market")],
        [InlineKeyboardButton(L['menu_interval'], callback_data="set_interval")],
        [InlineKeyboardButton(L['menu_threshold'], callback_data="set_threshold")],
        [InlineKeyboardButton(L['menu_direction'], callback_data="set_direction")],
        [InlineKeyboardButton(L['back'], callback_data="back_main")]
    ]
    update.callback_query.edit_message_text(L['menu_settings'], reply_markup=InlineKeyboardMarkup(buttons))

def set_language_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    buttons = [
        [InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(t(chat_id, 'back'), callback_data="menu_settings")]
    ]
    update.callback_query.edit_message_text(t(chat_id, 'menu_language'), reply_markup=InlineKeyboardMarkup(buttons))

def set_exchange_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    buttons = [[InlineKeyboardButton(e.capitalize(), callback_data=f"exchange_{e}")] for e in EXCHANGES]
    buttons.append([InlineKeyboardButton(t(chat_id, 'back'), callback_data="menu_settings")])
    update.callback_query.edit_message_text(t(chat_id, 'menu_exchange'), reply_markup=InlineKeyboardMarkup(buttons))

def set_market_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = user_settings[chat_id]['lang']
    L = LANGUAGES[lang]['markets']
    buttons = [
        [InlineKeyboardButton(L[0], callback_data="market_futures")],
        [InlineKeyboardButton(L[1], callback_data="market_spot")],
        [InlineKeyboardButton(t(chat_id, 'back'), callback_data="menu_settings")]
    ]
    update.callback_query.edit_message_text(t(chat_id, 'menu_market'), reply_markup=InlineKeyboardMarkup(buttons))

def set_interval_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = user_settings[chat_id]['lang']
    L = LANGUAGES[lang]['intervals']
    values = [30, 60, 120]
    buttons = [[InlineKeyboardButton(L[i], callback_data=f"interval_{values[i]}")] for i in range(len(values))]
    buttons.append([InlineKeyboardButton(t(chat_id, 'back'), callback_data="menu_settings")])
    update.callback_query.edit_message_text(t(chat_id, 'menu_interval'), reply_markup=InlineKeyboardMarkup(buttons))

def set_threshold_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    buttons = [[InlineKeyboardButton(f"{v}%", callback_data=f"threshold_{v}")] for v in [1, 2, 3, 5, 10]]
    buttons.append([InlineKeyboardButton(t(chat_id, 'back'), callback_data="menu_settings")])
    update.callback_query.edit_message_text(t(chat_id, 'menu_threshold'), reply_markup=InlineKeyboardMarkup(buttons))

def set_direction_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = user_settings[chat_id]['lang']
    L = LANGUAGES[lang]['directions']
    buttons = [
        [InlineKeyboardButton(L[0], callback_data="direction_pump")],
        [InlineKeyboardButton(L[1], callback_data="direction_dump")],
        [InlineKeyboardButton(L[2], callback_data="direction_both")],
        [InlineKeyboardButton(t(chat_id, 'back'), callback_data="menu_settings")]
    ]
    update.callback_query.edit_message_text(t(chat_id, 'menu_direction'), reply_markup=InlineKeyboardMarkup(buttons))
    # ===================== CALLBACK HANDLER =====================
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat.id

    if data.startswith('captcha_'):
        handle_captcha(update, context)
        return

    if not user_settings.get(chat_id, {}).get('captcha_passed'):
        query.answer(t(chat_id, 'captcha_required'), show_alert=True)
        emoji_captcha(update, context)
        return

    if data == 'menu_settings':
        settings_menu(update, context)
    elif data == 'set_lang':
        set_language_menu(update, context)
    elif data == 'set_exchange':
        set_exchange_menu(update, context)
    elif data == 'set_market':
        set_market_menu(update, context)
    elif data == 'set_interval':
        set_interval_menu(update, context)
    elif data == 'set_threshold':
        set_threshold_menu(update, context)
    elif data == 'set_direction':
        set_direction_menu(update, context)
    elif data == 'back_main':
        show_main_menu(update, context)
    elif data.startswith('lang_'):
        lang = data.split('_')[1]
        user_settings[chat_id]['lang'] = lang
        save_settings()
        settings_menu(update, context)
    elif data.startswith('exchange_'):
        user_settings[chat_id]['exchange'] = data.split('_')[1]
        save_settings()
        settings_menu(update, context)
    elif data.startswith('market_'):
        user_settings[chat_id]['market'] = data.split('_')[1]
        save_settings()
        settings_menu(update, context)
    elif data.startswith('interval_'):
        user_settings[chat_id]['interval'] = int(data.split('_')[1])
        save_settings()
        settings_menu(update, context)
    elif data.startswith('threshold_'):
        user_settings[chat_id]['threshold'] = float(data.split('_')[1])
        save_settings()
        settings_menu(update, context)
    elif data.startswith('direction_'):
        user_settings[chat_id]['direction'] = data.split('_')[1]
        save_settings()
        settings_menu(update, context)
    else:
        query.answer("Unknown action")
        # ===================== API MONITORING =====================
import aiohttp
import asyncio

async def fetch_binance():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://fapi.binance.com/fapi/v1/ticker/24hr") as resp:
            return await resp.json()

async def fetch_bybit():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.bybit.com/v5/market/tickers?category=linear") as resp:
            res = await resp.json()
            return res.get("result", {}).get("list", [])

async def fetch_mexc():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://contract.mexc.com/api/v1/contract/ticker") as resp:
            return await resp.json()

async def fetch_bingx():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://open-api.bingx.com/openApi/swap/v2/quote/ticker/24hr") as resp:
            return await resp.json()

async def fetch_kucoin():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api-futures.kucoin.com/api/v1/contracts/active") as resp:
            return await resp.json()

async def fetch_okx():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP") as resp:
            res = await resp.json()
            return res.get("data", [])

EXCHANGE_FETCHERS = {
    'binance': fetch_binance,
    'bybit': fetch_bybit,
    'mexc': fetch_mexc,
    'bingx': fetch_bingx,
    'kucoin': fetch_kucoin,
    'okx': fetch_okx
}

def get_price_change(entry, exchange):
    try:
        if exchange == 'binance':
            change = float(entry['priceChangePercent'])
            symbol = entry['symbol']
        elif exchange == 'bybit':
            change = float(entry['price24hPcnt']) * 100
            symbol = entry['symbol']
        elif exchange == 'mexc':
            change = float(entry['riseFall'])
            symbol = entry['symbol']
        elif exchange == 'bingx':
            change = float(entry['priceChangePercent'])
            symbol = entry['symbol']
        elif exchange == 'kucoin':
            change = float(entry['changeRate']) * 100
            symbol = entry['symbol']
        elif exchange == 'okx':
            change = float(entry['chg']) * 100
            symbol = entry['instId']
        else:
            return None, None
        return change, symbol
    except:
        return None, None

async def monitor_loop_async(bot):
    while True:
        for chat_id, settings in user_settings.items():
            if not settings.get('captcha_passed'):
                continue

            exchange = settings.get('exchange', 'binance')
            direction = settings.get('direction', 'both')
            threshold = settings.get('threshold', 5.0)
            interval = settings.get('interval', 60)
            last_notify = settings.get('last_notify', 0)

            fetcher = EXCHANGE_FETCHERS.get(exchange)
            if not fetcher:
                continue

            try:
                data = await fetcher()
                now = time.time()
                if now - last_notify < interval:
                    continue

                count = 0
                for entry in data:
                    change, symbol = get_price_change(entry, exchange)
                    if change is None or symbol is None:
                        continue
                    if abs(change) < threshold:
                        continue
                    if direction == 'pump' and change < 0:
                        continue
                    if direction == 'dump' and change > 0:
                        continue

                    key = 'alert_pump' if change > 0 else 'alert_dump'
                    emoji = "🚀" if change > 0 else "📉"
                    text = t(chat_id, key, percent=change, seconds=interval, emoji=emoji)
                    await bot.send_message(chat_id, text)
                    count += 1
                    if count >= 3:
                        break
                user_settings[chat_id]['last_notify'] = now
            except Exception as e:
                logging.warning(f"Monitor error ({exchange}): {e}")
        await asyncio.sleep(5)

def run_async_monitor(bot):
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_loop_async(bot))
    # ===================== TELEGRAM LAUNCH =====================
from telegram.ext import Defaults

def main():
    defaults = Defaults(parse_mode='HTML')
    updater = Updater(BOT_TOKEN, use_context=True, defaults=defaults)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", show_main_menu))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL
    )

    run_async_monitor(updater.bot)
    updater.idle()

if __name__ == '__main__':
    main()
