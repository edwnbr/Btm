import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import requests
from flask import Flask, request
import threading
import time

# Настройки
TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
WEBHOOK_URL = "https://btm-c4tt.onrender.com/" + TOKEN

# Инициализация Flask-приложения
app = Flask(__name__)

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Стартовые состояния
LANGUAGE, MENU = range(2)

# Данные пользователей
user_data = {}

# Языковые пакеты
texts = {
    'ru': {
        'start': "🌐 Выберите язык / Select language:",
        'menu': "⚙️ Главное меню:",
        'settings': "🛠 Настройки сохранены.",
        'choose_exchange': "🏦 Выберите биржу:",
        'choose_market': "📊 Выберите тип рынка:",
        'choose_timeframe': "⏱ Выберите таймфрейм:",
        'choose_threshold': "📈 Выберите порог изменения (%):",
        'choose_notify': "⚡ Выберите тип уведомлений:",
        'ai_analysis': "🤖 AI-анализ активирован.",
        'back': "🔙 Назад в меню",
    },
    'en': {
        'start': "🌐 Choose language:",
        'menu': "⚙️ Main menu:",
        'settings': "🛠 Settings saved.",
        'choose_exchange': "🏦 Choose exchange:",
        'choose_market': "📊 Choose market type:",
        'choose_timeframe': "⏱ Choose timeframe:",
        'choose_threshold': "📈 Choose threshold change (%):",
        'choose_notify': "⚡ Choose notification type:",
        'ai_analysis': "🤖 AI analysis activated.",
        'back': "🔙 Back to menu",
    }
}

reply_keyboards = {
    'language': [['🇷🇺 Русский', '🇺🇸 English']],
    'main_ru': [['🏦 Биржа', '📊 Рынок'], ['⏱ Таймфрейм', '📈 Порог %'], ['⚡ Уведомления', '🤖 AI-анализ'], ['🔄 Мои настройки']],
    'main_en': [['🏦 Exchange', '📊 Market'], ['⏱ Timeframe', '📈 Threshold %'], ['⚡ Notifications', '🤖 AI analysis'], ['🔄 My Settings']],
}

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(texts['ru']['start'], reply_markup=ReplyKeyboardMarkup(reply_keyboards['language'], resize_keyboard=True))
    return LANGUAGE

def language(update: Update, context: CallbackContext) -> int:
    lang = 'ru' if 'Русский' in update.message.text else 'en'
    user_id = update.effective_user.id
    user_data[user_id] = {'lang': lang}
    markup = ReplyKeyboardMarkup(reply_keyboards[f'main_{lang}'], resize_keyboard=True)
    update.message.reply_text(texts[lang]['menu'], reply_markup=markup)
    return MENU

def menu_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    lang = user_data.get(user_id, {}).get('lang', 'en')
    msg = update.message.text
    reply = ReplyKeyboardMarkup(reply_keyboards[f'main_{lang}'], resize_keyboard=True)
    update.message.reply_text(texts[lang]['menu'], reply_markup=reply)
    return MENU

def webhook():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(Filters.text & ~Filters.command, language)],
            MENU: [MessageHandler(Filters.text & ~Filters.command, menu_handler)],
        },
        fallbacks=[],
    )

    dp.add_handler(conv_handler)

    updater.start_webhook(listen="0.0.0.0", port=8443, url_path=TOKEN, webhook_url=WEBHOOK_URL)
    updater.idle()

@app.route("/" + TOKEN, methods=["POST"])
def telegram_webhook():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Запуск
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    webhook()
