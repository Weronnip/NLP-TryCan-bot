import os
import re
import ssl
import nltk
import base64
import telebot
import logging
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from nltk.sentiment import SentimentIntensityAnalyzer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ssl._create_default_https_context = ssl._create_unverified_context
nltk.download('vader_lexicon')

load_dotenv()
API_TOKEN = os.getenv("TOKEN_BOT")
YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY")
YANDEX_IAM_TOKEN = os.getenv("IAM_TOKEN") 
YANDEX_FOLDER_ID=os.getenv("YANDEX_FOLDER_ID")
CATALOG_ID = os.getenv("CATALOG_ID")


if not API_TOKEN:
    logging.error("API_TOKEN не найден! Проверь .env файл.")
    exit(1)

if not YANDEX_GPT_API_KEY or not CATALOG_ID:
    logging.warning("YANDEX_GPT_API_KEY или CATALOG_ID не найдены! Функция генерации текста не будет работать.")

if not YANDEX_IAM_TOKEN:
    logging.warning("YANDEX_IAM_TOKEN не найден! Функции синтеза речи могут не работать корректно.")

bot = telebot.TeleBot(API_TOKEN)
sia = SentimentIntensityAnalyzer()

user_in_generate_mode = {}

def generate_text_with_yandex_ai(prompt):
    try:
        logging.info("Отправка запроса к Yandex Cloud GPT...")
        headers = {
            "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"gpt://{CATALOG_ID}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 1,
                "maxTokens": 1000
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

def translate_text_with_yandex(text, source_lang='en', target_lang='ru'):
    try:
        url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        headers = {
            "Authorization": f"Api-Key {YANDEX_GPT_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "sourceLanguageCode": source_lang,
            "targetLanguageCode": target_lang,
            "texts": [text]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        translated_text = result['translations'][0]['text']
        return translated_text
    except Exception as e:
        logging.error(f"Ошибка при переводе: {e}")
        return "Ошибка перевода текста."

def text_to_speech(text):
    try:
        tts_url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
        headers = {
            "Authorization": f"Bearer {YANDEX_IAM_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "audio/mp3"
        }
        payload = {
            "text": text,
            "lang": "ru-RU",
            "voice": "alexander",
            "speed": 1.1,
            "format": "mp3",
            "folderId": YANDEX_FOLDER_ID,
        }

        # Отправка POST-запроса
        logging.info(f"Отправка запроса в Yandex TTS API с текстом: {text[:30]}...")  # Логируем начало текста
        response = requests.post(tts_url, headers=headers, data=payload)
        
        # Логируем статус ответа и текст
        logging.info(f"Ответ от API: Статус {response.status_code}")
        if response.status_code != 200:
            logging.error(f"Ответ от API: {response.text}")
            return None
        
        # Сохранение аудиофайла
        audio_file = f"speech_{abs(hash(text))}.mp3"
        with open(audio_file, "wb") as f:
            f.write(response.content)

        logging.info(f"Аудиофайл сохранен как {audio_file}")
        return audio_file

    except Exception as e:
        logging.error(f"Ошибка при синтезе речи: {e}")
        return None

def search_museum_info_api(museum_name):
    """
    Выполняет GET-запрос к Yandex XML Search API для получения информации о музее.
    Использует параметры запроса: query, l10n, sortby, filter, maxpassages и groupby.
    Для доступа требуются переменные YANDEX_XML_USER и YANDEX_XML_API_KEY.
    """
    try:
        search_url = "https://yandex.ru/search/xml"
        params = {
            "query": museum_name,
            "l10n": "ru",
            "sortby": "tm.order=descending",
            "filter": "strict",
            "maxpassages": "4",
            "groupby": "attr=mode=flat.groups-on-page=10.docs-in-group=1",
            "user": YANDEX_IAM_TOKEN,
            "key": YANDEX_IAM_TOKEN
        }
        response = requests.get(search_url, params=params)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        doc = root.find('.//doc')
        snippet = None
        if doc is not None:
            passage = doc.find('.//passage')
            if passage is not None and passage.text:
                snippet = passage.text.strip()
            else:
                title = doc.find('title')
                if title is not None and title.text:
                    snippet = title.text.strip()
        return snippet if snippet else "Информация не найдена."
    except Exception as e:
        logging.error(f"Ошибка при поиске информации о музее: {e}")
        return "Ошибка поиска информации."

def create_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(telebot.types.KeyboardButton("👨‍💻 AI ассистент"), telebot.types.KeyboardButton("🌍 Перевести"))
    keyboard.row(telebot.types.KeyboardButton("📊 Анализировать"), telebot.types.KeyboardButton("⚙️ Установить языки"))
    keyboard.add(telebot.types.KeyboardButton("❓ Помощь"))
    keyboard.add(telebot.types.KeyboardButton("👨‍💼 Аудио Гид"))
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я TryCan бот🤖.\nНапиши '👨‍💻 AI ассистент' для генерации текста или выбери команду из клавиатуры.", reply_markup=create_keyboard())

def analyze_image_without_text(image_path):
    """Отправляет изображение в Yandex Vision для анализа объектов"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
        headers = {
            "Authorization": f"Bearer {YANDEX_IAM_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "analyze_specs": [{
                "content": encoded_image,
                "features": [{"type": "LABEL_DETECTION"}, {"type": "TEXT_DETECTION"}]
            }]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if "results" in result and result["results"]:
            objects = result["results"][0].get("labelAnnotations", [])
            scene_description = ", ".join([obj['description'] for obj in objects]) if objects else "Не удалось распознать объекты."
            return scene_description
        else:
            return "Не удалось распознать объекты на изображении."
    except Exception as e:
        logging.error(f"Ошибка при анализе изображения: {e}")
        return "Ошибка анализа изображения"

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    bot.reply_to(message, "Функция создания рассказа по изображению отключена.")

@bot.message_handler(func=lambda message: message.text.lower() == "📊 анализировать")
def analyze_text_handler(message):
    bot.reply_to(message, "Отправьте текст для анализа.")
    bot.register_next_step_handler(message, process_analyze)

def process_analyze(message):
    text_to_analyze = message.text
    thinking_message = bot.send_message(message.chat.id, "Размышляет...")
    try:
        analysis_prompt = f"Проанализируй следующий текст, определи язык, выдели ошибки и предложи советы по улучшению текста:\n\n{text_to_analyze}"
        response = generate_text_with_yandex_ai(analysis_prompt)
        formatted_response = f"*Результат анализа текста:*\n{response}"
        bot.edit_message_text(formatted_response, chat_id=message.chat.id, message_id=thinking_message.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при анализе текста: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "👨‍💻 ai ассистент")
def activate_generate_mode(message):
    bot.reply_to(message, "Ты активировал 👨‍💻 AI ассистент! Чтобы выйти, напиши: `спасибо тебе за помощь! до встречи!`", parse_mode="Markdown")
    user_in_generate_mode[message.chat.id] = True

def process_generate_text(message):
    prompt = message.text
    thinking_message = bot.send_message(message.chat.id, "Размышляет...")
    response = generate_text_with_yandex_ai(prompt)
    formatted_response = f"*Ответ от AI:*\n{response}"
    bot.edit_message_text(formatted_response, chat_id=message.chat.id, message_id=thinking_message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.lower() == "🌍 перевести")
def translate_text_handler(message):
    bot.reply_to(message, "Отправьте текст для перевода.")
    bot.register_next_step_handler(message, process_translate)

def process_translate(message):
    text_to_translate = message.text
    try:
        translated_text = translate_text_with_yandex(text_to_translate, from_lang, to_lang)
        bot.reply_to(message, f"Переведенный текст: *{translated_text}*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при переводе: {e}")

@bot.message_handler(func=lambda message: message.text.lower() == "⚙️ установить языки")
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

@bot.message_handler(func=lambda message: message.text.lower() == "❓ помощь")
def send_help(message):
    bot.reply_to(message, "Я могу:\n*1.* Генерировать текст с помощью Yandex GPT '👨‍💻 AI ассистент'.\n*2.* Переводить текст с одного языка на другой '🌍 Перевести'.\n*3.* Анализировать текст на ошибки и улучшение '📊 Анализировать'.\n*4.* Устанавливать языки перевода '⚙️ Установить языки'.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: user_in_generate_mode.get(message.chat.id, False))
def handle_generated_mode(message):
    prompt = message.text
    if prompt.lower() == "спасибо тебе за помощь! до встречи!":
        bot.reply_to(message, "До встречи!")
        user_in_generate_mode[message.chat.id] = False
    else:
        thinking_message = bot.send_message(message.chat.id, "Размышляет...")
        response = generate_text_with_yandex_ai(prompt)
        formatted_response = f"*Ответ от AI:*\n{response}"
        bot.edit_message_text(formatted_response, chat_id=message.chat.id, message_id=thinking_message.message_id, parse_mode="Markdown")

########################################
# Новый функционал: Аудио музей
########################################
@bot.message_handler(func=lambda message: message.text.lower() == "👨‍💼 аудио гид")
def ask_museum_name(message):
    bot.reply_to(message, "Введите точное название музея:")
    bot.register_next_step_handler(message, process_museum_audio)

def clean_text_for_speech(text):
    # Удаляем все спецсимволы, оставляем только буквы и пробелы
    return re.sub(r'[^\w\s]', '', text)

def process_museum_audio(message):
    museum_name = message.text.strip()
    
    # Шаг 1: Поиск информации о музее через Yandex XML Search API
    search_info = search_museum_info_api(museum_name)
    
    # Шаг 2: Генерация подробного описания музея через AI
    prompt = f"На основе следующей информации о музее '{museum_name}': {search_info}\nнапиши подробное описание музея для виртуального посещения."
    description = generate_text_with_yandex_ai(prompt)
    
    # Шаг 3: Очистка текста от спецсимволов
    cleaned_description = clean_text_for_speech(description)
    final_text = f"{cleaned_description}\nПриятного виртуального посещения музея {museum_name}!"
    
    # Шаг 4: Синтез речи
    audio_path = text_to_speech(final_text)
    if audio_path:
        with open(audio_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio)
        os.remove(audio_path)  # Чистим временный файл
    else:
        bot.reply_to(message, "Ошибка при синтезе речи.")

bot.polling(none_stop=True)