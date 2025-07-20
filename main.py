# main.py

import os
import time
import logging
import random
import threading
import requests
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackContext,
    MessageHandler, Filters, CallbackQueryHandler
)

# === CONFIG ===
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = 8443

logging.basicConfig(level=logging.INFO)
user_settings = {}
volume_history = {}

# === LANG ===
LANGUAGES = {
    'en': {
        'start': "👋 Welcome! Please verify you are human.",
        'captcha': "🤖 Tap the emoji: {target}",
        'captcha_pass': "✅ Verified!",
        'captcha_fail': "❌ Wrong emoji. Try again.",
        'captcha_required': "❗️ Please complete the captcha first.",
        'menu': "⚙️ Settings:",
        'choose_lang': "🌐 Choose language:",
        'choose_exchange': "📊 Choose exchange:",
        'choose_interval': "⏱ Choose interval:",
        'choose_threshold': "📈 Choose price change threshold:",
        'choose_notify': "🛎 Choose alert type:",
        'choose_market': "💹 Choose market type:",
        'lang_selected': "✅ Language set to English.",
        'exchange_selected': "✅ Exchange set to {exchange}.",
        'interval_selected': "✅ Interval set to {interval} sec.",
        'threshold_selected': "✅ Threshold set to {threshold}%",
        'market_selected': "✅ Market type set to {market}.",
        'notify_selected': "✅ Notify type set to {notify}.",
        'back': "⬅️ Back to menu",
        'alert_pump': "🚀 Price up {percent:.2f}% in {seconds}s {emoji}",
        'alert_dump': "📉 Price down {percent:.2f}% in {seconds}s {emoji}",
        'suspicious_alert': "⚠️ Suspicious volume spike detected!",
    },
    'ru': {
        'start': "👋 Добро пожаловать! Подтвердите, что вы не бот.",
        'captcha': "🤖 Нажми на эмодзи: {target}",
        'captcha_pass': "✅ Проверка пройдена!",
        'captcha_fail': "❌ Неверный смайл. Попробуйте снова.",
        'captcha_required': "❗️ Сначала пройдите капчу.",
        'menu': "⚙️ Настройки:",
        'choose_lang': "🌐 Выберите язык:",
        'choose_exchange': "📊 Выберите биржу:",
        'choose_interval': "⏱ Выберите интервал:",
        'choose_threshold': "📈 Выберите порог изменения цены:",
        'choose_notify': "🛎 Уведомления:",
        'choose_market': "💹 Выберите тип рынка:",
        'lang_selected': "✅ Язык установлен: Русский.",
        'exchange_selected': "✅ Биржа: {exchange}.",
        'interval_selected': "✅ Интервал: {interval} сек.",
        'threshold_selected': "✅ Порог: {threshold}%",
        'market_selected': "✅ Тип рынка: {market}.",
        'notify_selected': "✅ Тип уведомлений: {notify}.",
        'back': "⬅️ Назад в меню",
        'alert_pump': "🚀 Цена выросла на {percent:.2f}% за {seconds} сек {emoji}",
        'alert_dump': "📉 Цена упала на {percent:.2f}% за {seconds} сек {emoji}",
        'suspicious_alert': "⚠️ Обнаружен всплеск объема!",
    }
}

def t(chat_id, key, **kwargs):
    lang = user_settings.get(chat_id, {}).get('lang', 'en')
    return LANGUAGES[lang].get(key, key).format(**kwargs)

# === CAPTCHA ===
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
        show_menu(update, context)
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'))
        emoji_captcha(update, context)

# === MENU ===
def show_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    buttons = [
        [InlineKeyboardButton("🌐 Language / Язык", callback_data="set_lang")],
        [InlineKeyboardButton("📊 Биржа / Exchange", callback_data="set_exchange")],
        [InlineKeyboardButton("⏱ Интервал / Interval", callback_data="set_interval")],
        [InlineKeyboardButton("📈 Порог / Threshold", callback_data="set_threshold")],
        [InlineKeyboardButton("🛎 Уведомления / Alerts", callback_data="set_notify")],
        [InlineKeyboardButton("💹 Рынок / Market", callback_data="set_market")]
    ]
    update.effective_message.reply_text(t(chat_id, 'menu'), reply_markup=InlineKeyboardMarkup(buttons))

# === START ===
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {
        'lang': 'ru',
        'exchange': 'binance',
        'threshold': 5.0,
        'interval': 60,
        'last_notify': 0,
        'captcha_passed': False,
        'market': 'futures',  # или 'spot'
        'notify_type': 'both'  # pump, dump, both
    }
    update.message.reply_text(t(chat_id, 'start'))
    emoji_captcha(update, context)

# === HANDLERS ===
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat.id

    if data.startswith('captcha_'):
        handle_captcha(update, context)
        return

    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        query.answer(t(chat_id, 'captcha_required'), show_alert=True)
        return

    # Здесь будут кнопки выбора языка, биржи и т.д.
    query.answer()
    # Обработка будет добавлена...

# === MONITORING ===
def monitor_loop(bot: Bot):
    while True:
        time.sleep(5)
        for chat_id, settings in user_settings.items():
            if not settings.get('captcha_passed'):
                continue
            try:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"  # будет зависеть от биржи
                response = requests.get(url, timeout=10)
                if not response.ok:
                    continue
                data = response.json()
                if not isinstance(data, list):
                    continue
                data = [d for d in data if isinstance(d, dict) and d.get("symbol", "").endswith("USDT")]

                for coin in data[:10]:
                    symbol = coin.get("symbol")
                    if not symbol:
                        continue
                    try:
                        price = float(coin["lastPrice"])
                        open_price = float(price / (1 + float(coin["priceChangePercent"]) / 100))
                        volume = float(coin["volume"])
                    except (KeyError, ValueError):
                        continue

                    if open_price == 0:
                        continue

                    change_percent = ((price - open_price) / open_price) * 100
                    if abs(change_percent) >= settings['threshold']:
                        now = time.time()
                        if now - settings['last_notify'] < settings['interval']:
                            continue

                        if settings['notify_type'] == 'pump' and change_percent < 0:
                            continue
                        if settings['notify_type'] == 'dump' and change_percent > 0:
                            continue

                        key = 'alert_pump' if change_percent > 0 else 'alert_dump'
                        emoji = "🚀" if change_percent > 0 else "📉"
                        text = t(chat_id, key, percent=change_percent, seconds=settings['interval'], emoji=emoji)
                        bot.send_message(chat_id, text)
                        user_settings[chat_id]['last_notify'] = now

                    avg_vol = volume_history.get(symbol, 0)
                    if avg_vol and volume > avg_vol * 3:
                        bot.send_message(chat_id, t(chat_id, 'suspicious_alert'))
                    volume_history[symbol] = (avg_vol * 0.9) + (volume * 0.1)

            except Exception as e:
                logging.warning(f"Monitor error: {e}")

# === TELEGRAM SETUP ===
updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, start))
dp.add_handler(CallbackQueryHandler(button_handler))

# === MAIN ===
if __name__ == '__main__':
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL
    )
    threading.Thread(target=monitor_loop, args=(updater.bot,), daemon=True).start()
    updater.idle()
