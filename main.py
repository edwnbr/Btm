import os
import json
import time
import threading
import logging
import asyncio
import aiohttp
import requests

from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler,
    Filters, CallbackContext
)

# === Настройки ===
TOKEN = '7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE'
APP_URL = 'https://btm-c4tt.onrender.com'  # Render-домен
bot = Bot(token=TOKEN)

# === Telegram Dispatcher ===
dispatcher = Dispatcher(bot, None, use_context=True)

# === Flask-приложение ===
app = Flask(__name__)

# === Логирование ===
logging.basicConfig(level=logging.INFO)

# === Временное хранилище пользователей ===
user_data = {}

# === Клавиатуры ===
main_menu_ru = [['📊 Биржа', '🕒 Таймфрейм'], ['📈 Порог (%)', '🔔 Тип уведомлений'], ['🧠 Язык', '⚙️ Мои настройки']]
main_menu_en = [['📊 Exchange', '🕒 Timeframe'], ['📈 Threshold (%)', '🔔 Notification type'], ['🧠 Language', '⚙️ My settings']]

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

# === Обработка CAPTCHA ===
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

# === Обработка текстовых сообщений ===
def handle_text(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text
    user = user_data.get(chat_id)

    if not user or not user.get('verified'):
        return handle_captcha(update, context)

    lang = user['lang']

    if text in ['🧠 Язык', '🧠 Language']:
        new_lang = 'en' if lang == 'ru' else 'ru'
        user['lang'] = new_lang
        msg = "🌐 Язык переключён на English" if new_lang == 'en' else "🌐 Language switched to Russian"
        context.bot.send_message(chat_id, msg, reply_markup=get_keyboard(new_lang))

    elif text in ['📊 Биржа', '📊 Exchange']:
        exchanges = ['Binance', 'Bybit', 'MEXC', 'BingX']
        current = user['exchange']
        new = exchanges[(exchanges.index(current) + 1) % len(exchanges)]
        user['exchange'] = new
        msg = f"📊 Биржа: {new}" if lang == 'ru' else f"📊 Exchange: {new}"
        context.bot.send_message(chat_id, msg)

    elif text in ['🕒 Таймфрейм', '🕒 Timeframe']:
        frames = ['1m', '5m', '15m']
        current = user['interval']
        new = frames[(frames.index(current) + 1) % len(frames)]
        user['interval'] = new
        msg = f"🕒 Таймфрейм: {new}" if lang == 'ru' else f"🕒 Timeframe: {new}"
        context.bot.send_message(chat_id, msg)

    elif text in ['📈 Порог (%)', '📈 Threshold (%)']:
        current = user['threshold']
        new = 1.0 if current >= 5.0 else round(current + 0.5, 1)
        user['threshold'] = new
        msg = f"📈 Порог изменения: {new}%" if lang == 'ru' else f"📈 Threshold: {new}%"
        context.bot.send_message(chat_id, msg)

    elif text in ['🔔 Тип уведомлений', '🔔 Notification type']:
        types = ['both', 'pump', 'dump']
        current = user['notif_type']
        new = types[(types.index(current) + 1) % len(types)]
        user['notif_type'] = new
        notif_names = {'both': '📈📉 Памп и дамп', 'pump': '📈 Только памп', 'dump': '📉 Только дамп'} if lang == 'ru' \
                      else {'both': '📈📉 Pump & Dump', 'pump': '📈 Pump only', 'dump': '📉 Dump only'}
        context.bot.send_message(chat_id, notif_names[new])

    elif text in ['⚙️ Мои настройки', '⚙️ My settings']:
        msg = (
            f"⚙️ Текущие настройки:\n"
            f"🌐 Язык: {'Русский' if lang == 'ru' else 'English'}\n"
            f"📊 Биржа: {user['exchange']}\n"
            f"🕒 Таймфрейм: {user['interval']}\n"
            f"📈 Порог: {user['threshold']}%\n"
            f"🔔 Тип: {user['notif_type']}"
        )
        context.bot.send_message(chat_id, msg)
    else:
        context.bot.send_message(chat_id, "Выберите действие из меню." if lang == 'ru' else "Please choose an option from the menu.")

# === Мониторинг API ===
async def fetch_data(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            return await response.json()
    except:
        return None

async def monitor():
    while True:
        async with aiohttp.ClientSession() as session:
            for chat_id, user in user_data.items():
                if not user.get('verified'):
                    continue
                exchange = user['exchange']
                market_type = user['market']
                interval = user['interval']
                threshold = user['threshold']
                notif_type = user['notif_type']
                lang = user['lang']

                url = get_api_url(exchange, market_type)
                data = await fetch_data(session, url)

                if data:
                    changes = analyze_data(data, threshold)
                    if changes:
                        text = format_message(changes, lang, notif_type)
                        if text:
                            try:
                                bot.send_message(chat_id, text)
                            except Exception as e:
                                logging.warning(f"Send message failed: {e}")
        await asyncio.sleep(30)

def get_api_url(exchange, market_type):
    if exchange == 'Binance':
        return "https://api.binance.com/api/v3/ticker/24hr"
    elif exchange == 'Bybit':
        return "https://api.bybit.com/v5/market/tickers?category=linear" if market_type == 'futures' \
            else "https://api.bybit.com/v5/market/tickers?category=spot"
    elif exchange == 'MEXC':
        return "https://api.mexc.com/api/v3/ticker/24hr"
    elif exchange == 'BingX':
        return "https://open-api.bingx.com/openApi/spot/v1/ticker/24hr"
    return ""

def analyze_data(data, threshold):
    results = []
    for item in data.get('result', {}).get('list', []) if isinstance(data, dict) else data:
        try:
            symbol = item.get('symbol') or item.get('s')
            change = float(item.get('priceChangePercent') or item.get('P'))
            if abs(change) >= threshold:
                results.append((symbol, change))
        except:
            continue
    return results

def format_message(changes, lang, notif_type):
    lines = []
    for symbol, change in changes:
        if notif_type == 'pump' and change < 0:
            continue
        if notif_type == 'dump' and change > 0:
            continue
        arrow = "📈" if change > 0 else "📉"
        percent = f"{change:.2f}%"
        lines.append(f"{arrow} {symbol}: {percent}")
    if not lines:
        return ""
    header = "🚨 Обнаружено движение на рынке:" if lang == 'ru' else "🚨 Market movement detected:"
    return f"{header}\n" + "\n".join(lines)

# === Flask роуты ===
@app.route('/')
def index():
    return 'Bot is running!'

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

# === Запуск ===
def start_flask():
    app.run(host='0.0.0.0', port=8080)

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(monitor())
    loop.run_forever()

# === Регистрация хендлеров ===
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

if __name__ == '__main__':
    threading.Thread(target=start_flask).start()
    start_bot()
