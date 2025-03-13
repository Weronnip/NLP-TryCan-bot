import telebot
import nltk
import ssl
import certifi
from nltk.sentiment import SentimentIntensityAnalyzer
from deep_translator import GoogleTranslator

ssl._create_default_https_context = ssl._create_unverified_context
nltk.download('vader_lexicon')

# Ваш токен Telegram-бота
API_TOKEN = '<API_KEY>'
bot = telebot.TeleBot(API_TOKEN)

# Создаем экземпляр анализатора настроений
sia = SentimentIntensityAnalyzer()

# Изначальные языковые настройки
from_lang = 'en'  # по умолчанию английский
to_lang = 'ru'  # по умолчанию русский

# Функция для создания клавиатуры с кнопками
def create_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton("/translate"))
    keyboard.add(telebot.types.KeyboardButton("/analyze"))
    keyboard.add(telebot.types.KeyboardButton("/setlang"))
    return keyboard

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я NLP-бот. Могу анализировать текст, переводить его и больше!\n"
                          "Выберите команду:", reply_markup=create_keyboard())

# Команда /help
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Я могу:\n"
                          "1. Анализировать ваш текст на позитивный/негативный/нейтральный.\n"
                          "2. Переводить текст с одного языка на другой.\n"
                          "3. Устанавливать языки для перевода с помощью команды /setlang.")

# Команда /setlang для установки языков перевода
@bot.message_handler(commands=['setlang'])
def set_language(message):
    global from_lang, to_lang
    bot.reply_to(message, "Введите языки для перевода в формате: <source_lang> <target_lang>\nПример: en ru")
    bot.register_next_step_handler(message, process_set_lang)

# Обработка ввода языков для перевода
def process_set_lang(message):
    global from_lang, to_lang
    try:
        new_from_lang, new_to_lang = message.text.split()
        from_lang = new_from_lang.lower()
        to_lang = new_to_lang.lower()
        bot.reply_to(message, f"Языки перевода установлены: {from_lang} -> {to_lang}.")
    except ValueError:
        bot.reply_to(message, "Неправильный формат. Используйте: <source_lang> <target_lang>.\nПример: en ru")

# Команда /translate для перевода текста
@bot.message_handler(commands=['translate'])
def translate_text_handler(message):
    bot.reply_to(message, "Отправьте текст для перевода.")
    bot.register_next_step_handler(message, process_translate)

# Обработка перевода
def process_translate(message):
    text_to_translate = message.text
    try:
        translation = translate_text(text_to_translate, from_lang, to_lang)
        bot.reply_to(message, f"Переведенный текст: {translation}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка при переводе: {e}")

# Команда /analyze для анализа текста
@bot.message_handler(commands=['analyze'])
def analyze_text_handler(message):
    bot.reply_to(message, "Отправьте текст для анализа.")
    bot.register_next_step_handler(message, process_analyze)

# Обработка анализа
def process_analyze(message):
    text_to_analyze = message.text
    sentiment = sia.polarity_scores(text_to_analyze)

    if sentiment['compound'] >= 0.05:
        response = "Ваш текст позитивный!"
    elif sentiment['compound'] <= -0.05:
        response = "Ваш текст негативный."
    else:
        response = "Ваш текст нейтральный."

    bot.reply_to(message, response)

# Функция для перевода текста через Google Translate
def translate_text(text, from_lang, to_lang):
    translation = GoogleTranslator(source=from_lang, target=to_lang).translate(text)
    return translation

# Запуск бота
bot.polling()
