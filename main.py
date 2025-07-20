import os
import time
import json
import logging
import random
import requests
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, Filters
)

# === CONFIG ===
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}/{BOT_TOKEN}"
PORT = 8443

# === GLOBALS ===
user_settings = {}
volume_history = {}
supported_exchanges = ['Binance', 'Bybit', 'MEXC', 'BingX', 'KuCoin', 'OKX']

# === LANG ===
LANGUAGES = {
    'en': {
        'start': "👋 Welcome! Please verify you are human.",
        'captcha': "🤖 Tap the emoji: {target}",
        'captcha_pass': "✅ Verified!",
        'captcha_fail': "❌ Wrong emoji. Try again.",
        'captcha_required': "❗️ Please complete the captcha first.",
        'select_lang': "🌐 Choose your language:",
        'select_exchange': "💱 Choose exchange:",
        'select_threshold': "📈 Select threshold (%):",
        'select_interval': "⏱️ Select interval:",
        'select_alert_type': "🔔 Alert type:",
        'alert_pump': "🚀 {symbol}: +{percent:.2f}% in {seconds}s",
        'alert_dump': "📉 {symbol}: -{percent:.2f}% in {seconds}s",
        'suspicious_alert': "⚠️ Suspicious volume spike detected!",
        'verified': "✅ You are verified.",
    },
    'ru': {
        'start': "👋 Добро пожаловать! Пожалуйста, подтвердите, что вы человек.",
        'captcha': "🤖 Нажмите на смайлик: {target}",
        'captcha_pass': "✅ Верификация пройдена!",
        'captcha_fail': "❌ Неверный смайлик. Попробуйте снова.",
        'captcha_required': "❗️ Пожалуйста, сначала пройдите капчу.",
        'select_lang': "🌐 Выберите язык:",
        'select_exchange': "💱 Выберите биржу:",
        'select_threshold': "📈 Выберите порог (%):",
        'select_interval': "⏱️ Выберите интервал:",
        'select_alert_type': "🔔 Тип уведомлений:",
        'alert_pump': "🚀 {symbol}: +{percent:.2f}% за {seconds}с",
        'alert_dump': "📉 {symbol}: -{percent:.2f}% за {seconds}с",
        'suspicious_alert': "⚠️ Обнаружен подозрительный всплеск объема!",
        'verified': "✅ Вы прошли верификацию.",
    }
}

def t(chat_id, key, **kwargs):
    lang = user_settings.get(chat_id, {}).get("lang", "en")
    return LANGUAGES.get(lang, LANGUAGES["en"]).get(key, key).format(**kwargs)

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
        show_settings_menu(update, context)
    else:
        query.edit_message_text(t(chat_id, 'captcha_fail'))
        emoji_captcha(update, context)

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {
        'lang': 'en',
        'exchange': 'Binance',
        'threshold': 5.0,
        'interval': 60,
        'alert_type': 'both',
        'captcha_passed': False
    }
    update.message.reply_text(t(chat_id, 'start'))
    emoji_captcha(update, context)

def text_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if not user_settings.get(chat_id, {}).get('captcha_passed', False):
        update.message.reply_text(t(chat_id, 'captcha_required'))
        emoji_captcha(update, context)
    else:
        update.message.reply_text(t(chat_id, 'verified'))
        show_settings_menu(update, context)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data

    if data.startswith("captcha_"):
        handle_captcha(update, context)
        return

    if not user_settings.get(chat_id, {}).get("captcha_passed"):
        query.answer(t(chat_id, "captcha_required"))
        return

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_settings[chat_id]["lang"] = lang
        query.answer("Language set.")
        show_settings_menu(update, context)

    elif data.startswith("exch_"):
        exchange = data.split("_")[1]
        user_settings[chat_id]["exchange"] = exchange
        query.answer("Exchange set.")
        show_settings_menu(update, context)

    elif data.startswith("th_"):
        user_settings[chat_id]["threshold"] = float(data.split("_")[1])
        query.answer("Threshold updated.")
        show_settings_menu(update, context)

    elif data.startswith("int_"):
        user_settings[chat_id]["interval"] = int(data.split("_")[1])
        query.answer("Interval updated.")
        show_settings_menu(update, context)

    elif data.startswith("alert_"):
        user_settings[chat_id]["alert_type"] = data.split("_")[1]
        query.answer("Alert type set.")
        show_settings_menu(update, context)

def show_settings_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = user_settings[chat_id].get("lang", "en")

    buttons = [
        [InlineKeyboardButton("🌐 Русский" if lang == "ru" else "🌐 English", callback_data="lang_ru" if lang == "en" else "lang_en")],
        [InlineKeyboardButton("💱 " + t(chat_id, 'select_exchange'), callback_data="exch_Binance")],
        [InlineKeyboardButton("📈 2%", callback_data="th_2"), InlineKeyboardButton("📈 5%", callback_data="th_5")],
        [InlineKeyboardButton("⏱️ 30s", callback_data="int_30"), InlineKeyboardButton("⏱️ 60s", callback_data="int_60")],
        [InlineKeyboardButton("🚀", callback_data="alert_pump"), InlineKeyboardButton("📉", callback_data="alert_dump"), InlineKeyboardButton("🔁", callback_data="alert_both")]
    ]
    context.bot.send_message(chat_id, t(chat_id, "select_lang"), reply_markup=InlineKeyboardMarkup(buttons))

def monitor_loop(bot):
    while True:
        time.sleep(5)
        for chat_id, settings in user_settings.items():
            if not settings.get('captcha_passed'):
                continue
            try:
                response = requests.get("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=10)
                data = response.json()
                data = [d for d in data if d.get("symbol", "").endswith("USDT")]
                for coin in data[:10]:
                    symbol = coin["symbol"]
                    price = float(coin["lastPrice"])
                    change_percent = float(coin["priceChangePercent"])
                    if abs(change_percent) >= settings["threshold"]:
                        if settings["alert_type"] == "pump" and change_percent < 0:
                            continue
                        if settings["alert_type"] == "dump" and change_percent > 0:
                            continue
                        bot.send_message(chat_id, t(chat_id, "alert_pump" if change_percent > 0 else "alert_dump",
                                                    symbol=symbol, percent=change_percent, seconds=settings["interval"]))
            except Exception as e:
                logging.warning(f"Monitor error: {e}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL
    )

    threading.Thread(target=monitor_loop, args=(updater.bot,), daemon=True).start()
    updater.idle()

if __name__ == '__main__':
    main()
