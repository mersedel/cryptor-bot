import os
import sys
import time
import threading
import json
from time import sleep
from flask import Flask
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
ENCRYPTION_JSON = os.getenv("ENCRYPTION_MAP_JSON")
PORT = int(os.getenv("PORT", 5000))

ENCRYPTION_MAP = json.loads(ENCRYPTION_JSON)
REVERSE_MAP = {v: k for k, v in ENCRYPTION_MAP.items()}


bot = telebot.TeleBot(BOT_TOKEN)


user_states = {}
user_modes = {}


log_lock = threading.Lock()

def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔐 Encrypt", "🔓 Decrypt")
    bot.send_message(chat_id, "Hello! Choose your mode:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_states[user_id] = "awaiting_password"
    bot.send_message(message.chat.id, "Hello! Please enter the password to use the bot:")


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    text = message.text.strip()
    time_str = time.strftime("%Y-%m-%d %H:%M:%S")

    if user_states.get(user_id) == "awaiting_password":
        if text == BOT_PASSWORD:
            user_states[user_id] = "authenticated"
            log_message(f"[{time_str}] AUTH SUCCESSFULY: {user_id} ({username}) — correct password")
            show_main_menu(message.chat.id)
        else:
            log_message(f"[{time_str}] AUTH FAIL: {user_id} ({username}) — wrong password: '{text}'")
            bot.send_message(message.chat.id, "❌ Incorrect password. Please try again.")
        return

    if user_states.get(user_id) == "authenticated":
        if text == "🔐 Encrypt":
            user_modes[user_id] = "encrypt"
            bot.send_message(message.chat.id, "Enter the text to encrypt:")
        elif text == "🔓 Decrypt":
            user_modes[user_id] = "decrypt"
            bot.send_message(message.chat.id, "Enter the text to decrypt:")
        elif user_id in user_modes:
            mode = user_modes[user_id]
            if mode == "encrypt":
                encrypted = encrypt(text)
                log_message(f"[{time_str}] ENCRYPT by {user_id} ({username}): '{text}' → '{encrypted}'")
                bot.send_message(message.chat.id, f"🔐 Encrypted:\n`{encrypted}`", parse_mode="Markdown")
            elif mode == "decrypt":
                decrypted = decrypt(text)
                log_message(f"[{time_str}] DECRYPT by {user_id} ({username}): '{text}' → '{decrypted}'")
                bot.send_message(message.chat.id, f"🔓 Decrypted:\n`{decrypted}`", parse_mode="Markdown")
        else:
            log_message(f"[{time_str}] NO MODE: {user_id} ({username}) — text: '{text}'")
            bot.send_message(message.chat.id, "Please choose a mode first.")
    else:
        log_message(f"[{time_str}] NO AUTH: {user_id} ({username}) — text: '{text}'")
        bot.send_message(message.chat.id, "Please use the /start command and enter the password.")


def encrypt(text):
    return ' '.join([ENCRYPTION_MAP.get(c.lower(), '?' if c != ' ' else ' ') for c in text])

def decrypt(text):
    return "".join([REVERSE_MAP.get(p, ' ' if p == '' else '?') for p in text.split(' ')]).replace("  ", " ")


def log_message(msg):
    with log_lock:
        sys.stdout.write('\n')
        sys.stdout.flush()
        print(msg)


app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive."

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()


print("\nBot started successfully!")


bot.polling(none_stop=True)