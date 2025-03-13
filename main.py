import os
import ssl
import nltk
import telebot
import logging
import requests
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from nltk.sentiment import SentimentIntensityAnalyzer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ssl._create_default_https_context = ssl._create_unverified_context
nltk.download('vader_lexicon')

load_dotenv()
API_TOKEN = os.getenv("TOKEN_BOT")
YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
CATALOG_ID = os.getenv("CATALOG_ID")

if not API_TOKEN:
    logging.error("API_TOKEN не найден! Проверь .env файл.")
    exit(1)

if not YANDEX_GPT_API_KEY or not CATALOG_ID:
    logging.warning("YANDEX_GPT_API_KEY или CATALOG_ID не найдены! Функция генерации текста не будет работать.")

bot = telebot.TeleBot(API_TOKEN)
sia = SentimentIntensityAnalyzer()
from_lang = 'en'
to_lang = 'ru'

def generate_text_with_yandex_ai(prompt):
    try:
        logging.info("Отправка запроса к Yandex Cloud GPT...")
        headers = {
            "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"gpt://{CATALOG_ID}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": 2000
            },
            "messages": [
                {"role": "system", "text": "Ты — полезный помощник."},
                {"role": "user", "text": prompt}
            ]
        }
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        generated_text = result.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "Ошибка в ответе Yandex GPT.")
        logging.info(f"Ответ от Yandex GPT: {generated_text}")
        return generated_text
    except Exception as e:
        logging.error(f"Ошибка при генерации текста: {e}")
        return "Ошибка генерации текста."

def create_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(telebot.types.KeyboardButton("/help"), telebot.types.KeyboardButton("/generate"))
    keyboard.row(telebot.types.KeyboardButton("/translate"), telebot.types.KeyboardButton("/analyze"))
    keyboard.add(telebot.types.KeyboardButton("/setlang"))
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я TryCan бот🤖. Напиши /help что бы посмотреть список доступных комманд", reply_markup=create_keyboard())

@bot.message_handler(commands=['generate'])
def generate_text_handler(message):
    bot.reply_to(message, "Отправьте текстовый запрос для генерации.")
    bot.register_next_step_handler(message, process_generate_text)

def process_generate_text(message):
    prompt = message.text
    response = generate_text_with_yandex_ai(prompt)
    bot.reply_to(message, response)

@bot.message_handler(commands=['setlang'])
def set_language(message):
    bot.reply_to(message, "Введите языки для перевода, example: ru en")
    bot.register_next_step_handler(message, process_set_lang)

def process_set_lang(message):
    global from_lang, to_lang
    try:
        new_from_lang, new_to_lang = message.text.split()
        from_lang, to_lang = new_from_lang.lower(), new_to_lang.lower()
        bot.reply_to(message, f"Языки установлены: {from_lang} -> {to_lang}.")
    except ValueError:
        bot.reply_to(message, "Ошибка! Используйте формат: en ru")

@bot.message_handler(commands=['translate'])
def translate_text_handler(message):
    bot.reply_to(message, "Отправьте текст для перевода.")
    bot.register_next_step_handler(message, process_translate)

def process_translate(message):
    text_to_translate = message.text
    try:
        translation = GoogleTranslator(source=from_lang, target=to_lang).translate(text_to_translate)
        bot.reply_to(message, f"Переведенный текст: {translation}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при переводе: {e}")

@bot.message_handler(commands=['analyze'])
def analyze_text_handler(message):
    bot.reply_to(message, "Отправьте текст для анализа.")
    bot.register_next_step_handler(message, process_analyze)

def process_analyze(message):
    text_to_analyze = message.text
    sentiment = sia.polarity_scores(text_to_analyze)
    response = "Ваш текст нейтральный."
    if sentiment['compound'] >= 0.05:
        response = "Ваш текст позитивный!"
    elif sentiment['compound'] <= -0.05:
        response = "Ваш текст негативный."
    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Я могу:\n"
                          "1. Анализировать ваш текст на позитивный/негативный/нейтральный /analyze.\n"
                          "2. Переводить текст с одного языка на другой /translate.\n"
                          "3. Устанавливать языки для перевода с помощью команды /setlang. \n"
                          "4. Генерировать текст с помощью Yandex GPT /generate.")

bot.polling(none_stop=True)
