from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging, json, time

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Словарь для хранения настроек пользователей
user_settings = {}

# Языковые пакеты
LANGUAGES = {
    "ru": {
        "start": "Привет! Выбери язык / Choose language:",
        "language_selected": "Язык установлен: Русский",
        "choose_exchange": "Выберите биржу:",
        "choose_market": "Выберите рынок:",
        "spot": "Спот",
        "futures": "Фьючерсы",
        "choose_timeframe": "Выберите таймфрейм:",
        "choose_threshold": "Выберите порог изменения (%):",
        "settings_saved": "Настройки сохранены.",
        "my_settings": "Ваши текущие настройки:"
    },
    "en": {
        "start": "Hi! Choose your language:",
        "language_selected": "Language set: English",
        "choose_exchange": "Choose exchange:",
        "choose_market": "Choose market:",
        "spot": "Spot",
        "futures": "Futures",
        "choose_timeframe": "Choose timeframe:",
        "choose_threshold": "Choose threshold (%):",
        "settings_saved": "Settings saved.",
        "my_settings": "Your current settings:"
    }
}

default_reply = [["Binance", "Bybit"], ["MEXC", "BingX"], ["Spot", "Futures"], ["30s", "1m", "5m"], ["0.5%", "1%", "3%"], ["Мои настройки", "My settings"]]

# Стартовая команда
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_settings[chat_id] = {"language": "ru"}
    reply_markup = ReplyKeyboardMarkup([["Русский", "English"]], resize_keyboard=True)
    update.message.reply_text(LANGUAGES["ru"]["start"], reply_markup=reply_markup)

# Обработка сообщений
def handle_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    user = user_settings.get(chat_id, {"language": "ru"})
    lang = user["language"]

    if text.lower() in ["русский", "russian"]:
        user_settings[chat_id]["language"] = "ru"
        update.message.reply_text(LANGUAGES["ru"]["language_selected"])
    elif text.lower() in ["english", "английский"]:
        user_settings[chat_id]["language"] = "en"
        update.message.reply_text(LANGUAGES["en"]["language_selected"])
    elif text in ["Binance", "Bybit", "MEXC", "BingX"]:
        user_settings[chat_id]["exchange"] = text
    elif text.lower() in ["spot", "спот"]:
        user_settings[chat_id]["market"] = "spot"
    elif text.lower() in ["futures", "фьючерсы"]:
        user_settings[chat_id]["market"] = "futures"
    elif text in ["30s", "1m", "5m", "15m"]:
        user_settings[chat_id]["timeframe"] = text
    elif text in ["0.5%", "1%", "3%"]:
        user_settings[chat_id]["threshold"] = text
    elif text.lower() in ["мои настройки", "my settings"]:
        current = user_settings.get(chat_id, {})
        message = LANGUAGES[lang]["my_settings"] + "\n" + json.dumps(current, indent=2, ensure_ascii=False)
        update.message.reply_text(message)
        return

    reply_markup = ReplyKeyboardMarkup(default_reply, resize_keyboard=True)
    update.message.reply_text(LANGUAGES[lang]["settings_saved"], reply_markup=reply_markup)

# Основной запуск бота
def main():
    TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
# --- placeholder ---
