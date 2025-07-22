import os
import json
import time
import threading
import logging
import requests
import asyncio
import aiohttp

from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler
)

# === Константы ===
TOKEN = '7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE'
APP_URL = 'https://btm-c4tt.onrender.com'  # Render-домен
bot = Bot(token=TOKEN)

# === Flask и Dispatcher ===
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

# === Логирование ===
logging.basicConfig(level=logging.INFO)

# === Временное хранилище пользователей ===
user_data = {}
# === Клавиатуры ===
main_menu_ru = [['📊 Биржа', '🕒 Таймфрейм'], ['📈 Порог (%)', '🔔 Тип уведомлений'],
                ['💱 Рынок', '🧠 Язык'], ['⚙️ Мои настройки']]
main_menu_en = [['📊 Exchange', '🕒 Timeframe'], ['📈 Threshold (%)', '🔔 Notification type'],
                ['💱 Market', '🧠 Language'], ['⚙️ My settings']]

def get_keyboard(lang):
    return ReplyKeyboardMarkup(main_menu_ru if lang == 'ru' else main_menu_en, resize_keyboard=True)

# === /start ===
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_data[chat_id] = {
        'verified': False,
        'lang': 'ru',
        'exchange': 'Binance',
        'market': 'spot',
        'interval': '1m',
        'threshold': 1.5,
        'notif_type': 'both',
    }
    context.bot.send_message(chat_id, "🔐 Пройдите CAPTCHA: напишите число 321")

# === CAPTCHA-проверка ===
def handle_captcha(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text
    if chat_id in user_data and not user_data[chat_id].get('verified'):
        if text.strip() == '321':
            user_data[chat_id]['verified'] = True
            lang = user_data[chat_id]['lang']
            msg = "✅ Верификация пройдена!" if lang == 'ru' else "✅ Verification passed!"
            context.bot.send_message(chat_id, msg, reply_markup=get_keyboard(lang))
        else:
            context.bot.send_message(chat_id, "❌ Неверно. Попробуйте снова.")
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# === Inline-кнопки ===
def get_inline_keyboard(options, current, prefix):
    buttons = []
    for opt in options:
        label = f"{'✅' if opt == current else ''} {opt}"
        buttons.append([InlineKeyboardButton(label.strip(), callback_data=f"{prefix}:{opt}")])
    return InlineKeyboardMarkup(buttons)

# === reply-кнопки ===
def handle_menu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text
    if chat_id not in user_data or not user_data[chat_id].get('verified'):
        return

    lang = user_data[chat_id]['lang']

    if text in ['📊 Биржа', '📊 Exchange']:
        options = ['Binance', 'Bybit', 'MEXC', 'BingX']
        context.bot.send_message(chat_id, "Выберите биржу:" if lang == 'ru' else "Select exchange:",
                                 reply_markup=get_inline_keyboard(options, user_data[chat_id]['exchange'], 'exchange'))

    elif text in ['🕒 Таймфрейм', '🕒 Timeframe']:
        options = ['1m', '5m', '15m', '30m', '1h']
        context.bot.send_message(chat_id, "Выберите таймфрейм:" if lang == 'ru' else "Select timeframe:",
                                 reply_markup=get_inline_keyboard(options, user_data[chat_id]['interval'], 'interval'))

    elif text in ['📈 Порог (%)', '📈 Threshold (%)']:
        options = ['0.5', '1', '2', '3', '5']
        context.bot.send_message(chat_id, "Выберите порог изменения в %:" if lang == 'ru' else "Select % change threshold:",
                                 reply_markup=get_inline_keyboard(options, str(user_data[chat_id]['threshold']), 'threshold'))

    elif text in ['🔔 Тип уведомлений', '🔔 Notification type']:
        options = ['pump', 'dump', 'both']
        context.bot.send_message(chat_id, "Выберите тип уведомлений:" if lang == 'ru' else "Select notification type:",
                                 reply_markup=get_inline_keyboard(options, user_data[chat_id]['notif_type'], 'notif'))

    elif text in ['💱 Рынок', '💱 Market']:
        options = ['spot', 'futures']
        context.bot.send_message(chat_id, "Выберите рынок:" if lang == 'ru' else "Select market:",
                                 reply_markup=get_inline_keyboard(options, user_data[chat_id]['market'], 'market'))

    elif text in ['🧠 Язык', '🧠 Language']:
        options = ['ru', 'en']
        context.bot.send_message(chat_id, "Выберите язык:" if lang == 'ru' else "Select language:",
                                 reply_markup=get_inline_keyboard(options, user_data[chat_id]['lang'], 'lang'))

    elif text in ['⚙️ Мои настройки', '⚙️ My settings']:
        u = user_data[chat_id]
        summary = (
            f"📊 Биржа: {u['exchange']}\n"
            f"💱 Рынок: {u['market']}\n"
            f"🕒 Таймфрейм: {u['interval']}\n"
            f"📈 Порог: {u['threshold']}%\n"
            f"🔔 Тип уведомлений: {u['notif_type']}\n"
            f"🧠 Язык: {u['lang']}"
        ) if lang == 'ru' else (
            f"📊 Exchange: {u['exchange']}\n"
            f"💱 Market: {u['market']}\n"
            f"🕒 Timeframe: {u['interval']}\n"
            f"📈 Threshold: {u['threshold']}%\n"
            f"🔔 Notification type: {u['notif_type']}\n"
            f"🧠 Language: {u['lang']}"
        )
        context.bot.send_message(chat_id, summary)
        # === Обработка inline-кнопок ===
def inline_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
    data = query.data

    if ':' not in data:
        return

    key, value = data.split(':', 1)
    if key in ['exchange', 'interval', 'threshold', 'notif', 'lang', 'market']:
        user_data[chat_id][key if key != 'notif' else 'notif_type'] = value if key != 'threshold' else float(value)
        lang = user_data[chat_id]['lang']
        query.answer("Обновлено!" if lang == 'ru' else "Updated!")
        query.edit_message_text("✅ Обновлено!" if lang == 'ru' else "✅ Updated!")

# === Команда AI-анализа ===
def ai_analysis(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id not in user_data or not user_data[chat_id].get('verified'):
        return

    msg = update.message.text.strip()
    parts = msg.split()
    if len(parts) < 2:
        update.message.reply_text("Пример: AI BTC" if user_data[chat_id]['lang'] == 'ru' else "Example: AI BTC")
        return

    symbol = parts[1].upper()
    exchange = user_data[chat_id]['exchange']
    interval = user_data[chat_id]['interval']
    market = user_data[chat_id]['market']
    lang = user_data[chat_id]['lang']

    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval={interval}"
        res = requests.get(url)
        data = res.json()

        if not isinstance(data, list):
            raise ValueError()

        close_prices = [float(k[4]) for k in data[-5:]]
        volumes = [float(k[5]) for k in data[-5:]]

        price_change = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100
        volume_avg = sum(volumes[:-1]) / len(volumes[:-1])
        volume_now = volumes[-1]
        volume_ratio = volume_now / volume_avg if volume_avg > 0 else 0

        if abs(price_change) < 0.3 and volume_ratio < 1.2:
            trend = "боковик" if lang == 'ru' else "sideways"
        elif price_change > 0 and volume_ratio > 1.5:
            trend = "рост" if lang == 'ru' else "uptrend"
        elif price_change < 0 and volume_ratio > 1.5:
            trend = "падение" if lang == 'ru' else "downtrend"
        else:
            trend = "неопределённость" if lang == 'ru' else "uncertain"

        reply = f"🔍 AI-анализ монеты {symbol}:\n📈 Изменение: {price_change:.2f}%\n📊 Объём: {volume_now:.2f} (x{volume_ratio:.2f})\n📉 Вывод: {trend}" if lang == 'ru' else \
                f"🔍 AI analysis for {symbol}:\n📈 Change: {price_change:.2f}%\n📊 Volume: {volume_now:.2f} (x{volume_ratio:.2f})\n📉 Conclusion: {trend}"

        update.message.reply_text(reply)

    except Exception as e:
        update.message.reply_text("Ошибка анализа." if lang == 'ru' else "Analysis error.")
        # === Подключение всех хендлеров ===
def setup_dispatcher(dp):
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Мои настройки|My Settings)$'), show_settings))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Настройки|Settings)$'), settings_menu))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Язык|Language)$'), set_language))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Биржа|Exchange)$'), set_exchange))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Интервал|Interval)$'), set_interval))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Порог|Threshold)$'), set_threshold))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Тип уведомлений|Notification Type)$'), set_notif_type))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(Рынок|Market)$'), set_market))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^(AI|АИ)\s+[A-Za-z]+'), ai_analysis))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))
    dp.add_handler(MessageHandler(Filters.command, start))
    dp.add_handler(MessageHandler(Filters.all, start))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(MessageHandler(Filters.regex(r'^.+$'), start))

    dp.add_handler(MessageHandler(Filters.callback_query, inline_handler))

# === Flask-сервер ===
TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=4)

setup_dispatcher(dispatcher)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
