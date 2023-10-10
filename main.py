import os
from telebot import types

import requests
import telebot

import psycopg2
from psycopg2 import sql
import speech_recognition as sr
from pydub import AudioSegment

from config import TOKEN, DATABASE_URL

bot = telebot.TeleBot(TOKEN)

conn = psycopg2.connect(DATABASE_URL)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Добавить идею")
    item2 = types.KeyboardButton("Поиск по хештегу")
    markup.add(item1, item2)
    bot.reply_to(message, "Привет! Этот бот поможет вам записывать ваши мысли.", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Добавить мысль")
def add_thought(message):
    bot.send_message(message.chat.id, "Пожалуйста, отправьте вашу мысль или аудиосообщение для записи. Не забудь поставить или сказать хештег, для более удобного поиска.")
    bot.register_next_step_handler(message, process_idea)


def process_idea(message):
    user_id = message.from_user.id
    text = message.text
    if message.voice:
        try:
            file_info = bot.get_file(message.voice.file_id)
            file_path = file_info.file_path
            audio_url = f'https://api.telegram.org/file/bot{bot.token}/{file_path}'

            audio_file = 'audio.ogg'
            response = requests.get(audio_url)
            with open(audio_file, 'wb') as file:
                file.write(response.content)

            ogg_audio = AudioSegment.from_file(audio_file, format="ogg")
            ogg_audio.export("audio.wav", format="wav")

            r = sr.Recognizer()
            with sr.AudioFile("audio.wav") as source:
                audio = r.record(source)

            text = r.recognize_google(audio, language="ru-RU")

            bot.send_message(message.chat.id, f'Распознанный текст: {text}')

            os.remove(audio_file)
            os.remove("audio.wav")

        except Exception as e:
            bot.send_message(message.chat.id, f'Произошла ошибка: {str(e)}')

    hashtags = [word.lower() for word in text.split() if word.startswith("#")]

    cursor = conn.cursor()
    insert_query = sql.SQL("""
        INSERT INTO test (user_id, text, hashtags)
        VALUES (%s, %s, %s)
    """)
    cursor.execute(insert_query, (user_id, text, hashtags))
    conn.commit()
    cursor.close()

    bot.send_message(message.chat.id, "Идея успешно сохранена!")


@bot.message_handler(func=lambda message: message.text == "Поиск по хештегу")
def get_thoughts(message):
    bot.send_message(message.chat.id, "Пожалуйста, отправьте хештег для поиска идей. Не забудь решетку.")
    bot.register_next_step_handler(message, process_hashtag)


def process_hashtag(message):
    hashtag = message.text.lower()
    cursor = conn.cursor()
    select_query = sql.SQL(f"""
        SELECT * FROM test WHERE '{hashtag}' = ANY(hashtags)
    """)
    cursor.execute(select_query, [hashtag])
    thoughts = cursor.fetchall()
    cursor.close()

    if thoughts:
        bot.send_message(message.chat.id, f"Идеи с хештегом {hashtag}:")
        for thought in thoughts:
            bot.send_message(message.chat.id, thought[2])
    else:
        bot.send_message(message.chat.id, f"Идеи с хештегом {hashtag} не найдены.")


if __name__ == "__main__":
    bot.polling()
