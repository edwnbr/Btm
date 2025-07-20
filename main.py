import os
import time
import logging
import random
import threading
import requests
from flask import Flask, request
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackContext,
    MessageHandler, Filters, CallbackQueryHandler
)

# ===================== CONFIG =====================

BOT_TOKEN = '7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE'  # ВСТАВЬ СЮДА СВОЙ ТОКЕН
WEBHOOK_HOST = 'https://btm-c4tt.onrender.com'  # ВСТАВЬ СЮДА СВОЙ РЕНДЕР URL
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

user_settings = {}
volume_history = {}

# ===================== ЛОКАЛИЗАЦИЯ =====================

LANGUAGES = {
    'en': {
        'start': "👋 Welcome! Please verify you are human.",
        'captcha': "🤖 Tap the emoji: {target}",
        'captcha_pass': "✅ Verified!",
        'captcha_fail': "❌ Wrong emoji. Try again.",
        'captcha_required': "❗️ Please complete the captcha first.",
        'btn_captcha_again': "🔒 Retry captcha",
        'alert_pump': "🚀 Price up {percent:.2f}% in {seconds}s {emoji}",
        'alert_dump': "📉 Price down {percent:.2f}% in {seconds}s {emoji}",
        'suspicious_alert': "⚠️ Suspicious volume spike detected!",
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
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'))
        emoji_captcha(update, context)

# ===================== HANDLERS =====================

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {
        'lang': 'en',
        'exchange': 'bin',
        'threshold': 5.0,
        'interval': 60,
        'last_notify': 0,
        'captcha_passed': False,
    }
    update.message.reply_text(t(chat_id, 'start'))
    emoji_captcha(update, context)

def text_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        update.message.reply_text(t(chat_id, 'captcha_required'))
        emoji_captcha(update, context)
    else:
        update.message.reply_text("✅ You are verified.")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    if data.startswith('captcha_'):
        handle_captcha(update, context)
    elif data == 'start_captcha':
        emoji_captcha(update, context)

# ===================== MONITORING =====================

def monitor_loop(bot):
    while True:
        time.sleep(5)
        for chat_id, settings in user_settings.items():
            if not settings.get('captcha_passed'):
                continue

            try:
                url = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
                data = requests.get(url, timeout=10).json()
                data = [d for d in data if d['symbol'].endswith('USDT')]

                for coin in data[:10]:
                    symbol = coin['symbol']
                    try:
                        price = float(coin['lastPrice'])
                        open_price = float(price / (1 + float(coin['priceChangePercent']) / 100))
                        volume = float(coin['volume'])
                    except:
                        continue

                    if open_price == 0:
                        continue

                    change_percent = ((price - open_price) / open_price) * 100
                    if abs(change_percent) >= settings['threshold']:
                        now = time.time()
                        if now - settings['last_notify'] < settings['interval']:
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

# ===================== TELEGRAM SETUP =====================

updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
dp.add_handler(CallbackQueryHandler(button_handler))

# ===================== FLASK WEBHOOK =====================

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), updater.bot)
    dp.process_update(update)
    return "ok"

@app.route('/')
def index():
    return "Bot is alive!"

# ===================== MAIN =====================

if __name__ == '__main__':
    # Установим вебхук
    updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        url_path=BOT_TOKEN
    )
    updater.bot.set_webhook(WEBHOOK_URL)

    # Запуск фонового мониторинга
    threading.Thread(target=monitor_loop, args=(updater.bot,), daemon=True).start()

    # Flask сервер
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8443)))
