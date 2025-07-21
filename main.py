
import logging
import os
import json
import requests
import threading
import time
from flask import Flask, request
from telegram import (
    Bot, Update, ReplyKeyboardMarkup
)
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
)

# ===================== CONFIG =====================
BOT_TOKEN = "7697812728:AAG72LwVSOhN-v1kguh3OPXK9BzXffJUrYE"
RENDER_EXTERNAL_HOSTNAME = "btm-c4tt.onrender.com"
WEBHOOK_HOST = f"https://{RENDER_EXTERNAL_HOSTNAME}"
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get('PORT', 8443))

# ===================== LOGGING =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== APP =====================
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# ===================== USER DATA =====================
user_data = {}

# ===================== TRANSLATIONS =====================
texts = {
    "ru": {
        "start": "ð ÐÑÐ¸Ð²ÐµÑ! ÐÐ¾Ð´ÑÐ²ÐµÑÐ´Ð¸, ÑÑÐ¾ ÑÑ Ð½Ðµ Ð±Ð¾Ñ:",
        "captcha_passed": "â ÐÐµÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¸Ñ Ð¿ÑÐ¾ÑÐ»Ð° ÑÑÐ¿ÐµÑÐ½Ð¾!",
        "language_selected": "ð Ð¯Ð·ÑÐº ÑÑÑÐ°Ð½Ð¾Ð²Ð»ÐµÐ½: Ð ÑÑÑÐºÐ¸Ð¹",
        "menu": "ð ÐÑÐ±ÐµÑÐ¸ Ð´ÐµÐ¹ÑÑÐ²Ð¸Ðµ:",
        "settings": "âï¸ Ð¢ÐµÐºÑÑÐ¸Ðµ Ð½Ð°ÑÑÑÐ¾Ð¹ÐºÐ¸:",
        "confirm": "â ÐÑ Ð²ÑÐ±ÑÐ°Ð»Ð¸: ",
        "main_menu": [["ð Ð¯Ð·ÑÐº", "âï¸ ÐÐ°ÑÑÑÐ¾Ð¹ÐºÐ¸"], ["ð ÐÐ¸ÑÐ¶Ð°", "ð¹ Ð ÑÐ½Ð¾Ðº"], ["â± ÐÐ½ÑÐµÑÐ²Ð°Ð»", "ð ÐÐ¾ÑÐ¾Ð³"], ["ð Ð¢Ð¸Ð¿ ÑÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸Ð¹"]],
        "choose_language": "ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ·ÑÐº:",
        "choose_exchange": "ÐÑÐ±ÐµÑÐ¸ÑÐµ Ð±Ð¸ÑÐ¶Ñ:",
        "choose_market": "ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÑÐ½Ð¾Ðº:",
        "choose_interval": "ÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¸Ð½ÑÐµÑÐ²Ð°Ð»:",
        "choose_threshold": "ÐÑÐ±ÐµÑÐ¸ÑÐµ Ð¿Ð¾ÑÐ¾Ð³ Ð¸Ð·Ð¼ÐµÐ½ÐµÐ½Ð¸Ñ (%):",
        "choose_notify_type": "ÐÑÐ±ÐµÑÐ¸ÑÐµ ÑÐ¸Ð¿ ÑÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸Ð¹:",
        "spot": "Ð¡Ð¿Ð¾Ñ",
        "futures": "Ð¤ÑÑÑÐµÑÑÑ",
        "pump": "ÐÐ°Ð¼Ð¿",
        "dump": "ÐÐ°Ð¼Ð¿",
        "both": "ÐÐ±Ð°",
        "settings_applied": "â ÐÐ°ÑÑÑÐ¾Ð¹ÐºÐ¸ ÑÐ¾ÑÑÐ°Ð½ÐµÐ½Ñ.",
        "not_verified": "ð« Ð¡Ð½Ð°ÑÐ°Ð»Ð° Ð¿ÑÐ¾Ð¹Ð´Ð¸ÑÐµ Ð²ÐµÑÐ¸ÑÐ¸ÐºÐ°ÑÐ¸Ñ CAPTCHA."
    },
    "en": {
        "start": "ð Hello! Please verify you're not a bot:",
        "captcha_passed": "â Verification successful!",
        "language_selected": "ð Language set to: English",
        "menu": "ð Choose an action:",
        "settings": "âï¸ Current settings:",
        "confirm": "â You selected: ",
        "main_menu": [["ð Language", "âï¸ Settings"], ["ð Exchange", "ð¹ Market"], ["â± Interval", "ð Threshold"], ["ð Notify Type"]],
        "choose_language": "Choose language:",
        "choose_exchange": "Choose exchange:",
        "choose_market": "Choose market:",
        "choose_interval": "Choose interval:",
        "choose_threshold": "Choose % threshold:",
        "choose_notify_type": "Choose notification type:",
        "spot": "Spot",
        "futures": "Futures",
        "pump": "Pump",
        "dump": "Dump",
        "both": "Both",
        "settings_applied": "â Settings saved.",
        "not_verified": "ð« Please complete CAPTCHA first."
    }
}

exchanges = ["Binance", "Bybit", "MEXC", "BingX"]
intervals = ["30s", "1m", "3m", "5m"]
thresholds = ["1", "2", "3", "5", "10"]
notify_types = ["pump", "dump", "both"]

# ===================== KEYBOARDS =====================
def get_keyboard(lang):
    return ReplyKeyboardMarkup(
        keyboard=texts[lang]["main_menu"],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ===================== CAPTCHA & MENU =====================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {"verified": False, "lang": "en"}
    lang = "en"
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=texts[lang]["start"],
        reply_markup=ReplyKeyboardMarkup([["â I'm not a bot"]], resize_keyboard=True)
    )

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    message = update.message.text
    lang = user_data.get(user_id, {}).get("lang", "en")

    if not user_data.get(user_id, {}).get("verified"):
        if message in ["â I'm not a bot", "â Ð¯ Ð½Ðµ Ð±Ð¾Ñ"]:
            user_data[user_id]["verified"] = True
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=texts[lang]["captcha_passed"],
                reply_markup=get_keyboard(lang)
            )
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["not_verified"])
        return

    if message in ["ð Language", "ð Ð¯Ð·ÑÐº"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["choose_language"],
                                 reply_markup=ReplyKeyboardMarkup([["English", "Ð ÑÑÑÐºÐ¸Ð¹"]], resize_keyboard=True))
    elif message in ["English", "Ð ÑÑÑÐºÐ¸Ð¹"]:
        lang = "en" if message == "English" else "ru"
        user_data[user_id]["lang"] = lang
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["language_selected"],
                                 reply_markup=get_keyboard(lang))
    elif message in ["ð ÐÐ¸ÑÐ¶Ð°", "ð Exchange"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["choose_exchange"],
                                 reply_markup=ReplyKeyboardMarkup([exchanges], resize_keyboard=True))
    elif message in exchanges:
        user_data[user_id]["exchange"] = message
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["settings_applied"],
                                 reply_markup=get_keyboard(lang))
    elif message in ["ð¹ Ð ÑÐ½Ð¾Ðº", "ð¹ Market"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["choose_market"],
                                 reply_markup=ReplyKeyboardMarkup([[texts[lang]["spot"], texts[lang]["futures"]]], resize_keyboard=True))
    elif message in [texts[lang]["spot"], texts[lang]["futures"]]:
        user_data[user_id]["market"] = message
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["settings_applied"],
                                 reply_markup=get_keyboard(lang))
    elif message in ["â± ÐÐ½ÑÐµÑÐ²Ð°Ð»", "â± Interval"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["choose_interval"],
                                 reply_markup=ReplyKeyboardMarkup([intervals], resize_keyboard=True))
    elif message in intervals:
        user_data[user_id]["interval"] = message
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["settings_applied"],
                                 reply_markup=get_keyboard(lang))
    elif message in ["ð ÐÐ¾ÑÐ¾Ð³", "ð Threshold"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["choose_threshold"],
                                 reply_markup=ReplyKeyboardMarkup([thresholds], resize_keyboard=True))
    elif message in thresholds:
        user_data[user_id]["threshold"] = message
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["settings_applied"],
                                 reply_markup=get_keyboard(lang))
    elif message in ["ð Ð¢Ð¸Ð¿ ÑÐ²ÐµÐ´Ð¾Ð¼Ð»ÐµÐ½Ð¸Ð¹", "ð Notify Type"]:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["choose_notify_type"],
                                 reply_markup=ReplyKeyboardMarkup([[texts[lang]["pump"], texts[lang]["dump"], texts[lang]["both"]]], resize_keyboard=True))
    elif message in [texts[lang]["pump"], texts[lang]["dump"], texts[lang]["both"]]:
        user_data[user_id]["notify_type"] = message
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["settings_applied"],
                                 reply_markup=get_keyboard(lang))
    elif message in ["âï¸ ÐÐ°ÑÑÑÐ¾Ð¹ÐºÐ¸", "âï¸ Settings"]:
        settings = user_data.get(user_id, {})
        s_text = f"{texts[lang]['settings']}

"
        s_text += f"ð Language: {lang.upper()}
"
        s_text += f"ð Exchange: {settings.get('exchange', '-')}
"
        s_text += f"ð¹ Market: {settings.get('market', '-')}
"
        s_text += f"â± Interval: {settings.get('interval', '-')}
"
        s_text += f"ð Threshold: {settings.get('threshold', '-')}
"
        s_text += f"ð Notify: {settings.get('notify_type', '-')}
"
        context.bot.send_message(chat_id=update.effective_chat.id, text=s_text, reply_markup=get_keyboard(lang))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=texts[lang]["confirm"] + message,
                                 reply_markup=get_keyboard(lang))

# ===================== FLASK WEBHOOK =====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running."

# ===================== MAIN =====================
def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    main()
