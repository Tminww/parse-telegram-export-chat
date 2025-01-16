from bs4 import BeautifulSoup
import os
import speech_recognition as sr
from moviepy import VideoFileClip
import tempfile
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv  # Импортируем load_dotenv


# Загружаем переменные из .env файла

load_dotenv()


# Получаем значения из .env

NAME = os.getenv("NAME")  # Имя пользователя

CHAT_EXPORT_DIRECTORY = os.getenv(
    "CHAT_EXPORT_DIRECTORY"
)  # Директория с экспортированными файлами

PATH_TO_FFMPEG = os.getenv("PATH_TO_FFMPEG")  # Путь к ffmpeg

# Проверяем, что переменные загружены

if not NAME or not CHAT_EXPORT_DIRECTORY or not PATH_TO_FFMPEG:
    raise ValueError(
        "Пожалуйста, проверьте .env файл. Переменные NAME и CHAT_EXPORT_DIRECTORY, PATH_TO_FFMPEG должны быть заданы."
    )


CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


# Добавляем путь к PATH

os.environ["PATH"] += os.pathsep + PATH_TO_FFMPEG


# Функция для конвертации .ogg в .wav


def convert_ogg_to_wav(ogg_path):
    wav_path = tempfile.mktemp(suffix=".wav")

    audio = AudioSegment.from_ogg(ogg_path)

    audio.export(wav_path, format="wav")

    return wav_path


# Функция для извлечения аудио из видеофайла


def extract_audio_from_video(video_path):
    video = VideoFileClip(video_path)

    audio = video.audio

    temp_audio_path = tempfile.mktemp(suffix=".wav")

    audio.write_audiofile(temp_audio_path)

    return temp_audio_path


# Функция для распознавания текста из аудиофайла


def recognize_speech(audio_path):
    recognizer = sr.Recognizer()

    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language="ru-RU")

        return text

    except sr.UnknownValueError:
        return "Речь не распознана"

    except sr.RequestError:
        return "Ошибка сервиса распознавания"


# Функция для извлечения сообщений из одного файла


def extract_messages_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    messages = []

    for message in soup.find_all("div", class_="message default clearfix"):
        user_name = message.find("div", class_="from_name")

        if user_name and NAME in user_name.text.strip():
            # Извлечение времени сообщения

            time_element = message.find("div", class_="pull_right date details")

            timestamp = (
                time_element["title"]
                if time_element and "title" in time_element.attrs
                else "Нет времени"
            )

            timestamp = timestamp.replace("UTC", "").strip()

            timestamp = timestamp.split("+")[0].strip()

            # Проверка на текстовое сообщение

            text = message.find("div", class_="text")

            if text:
                print(f"{timestamp} - {text.text.strip()}")

                messages.append(f"{timestamp} {NAME} - {text.text.strip()}")

            else:
                # Проверка на голосовое сообщение

                voice_message = message.find("a", class_="media_voice_message")

                if voice_message and "href" in voice_message.attrs:
                    audio_path = os.path.join(
                        CHAT_EXPORT_DIRECTORY, voice_message["href"]
                    )

                    # print(audio_path)

                    if os.path.exists(audio_path):
                        try:
                            wav_path = convert_ogg_to_wav(
                                audio_path
                            )  # Конвертируем .ogg в .wav

                            recognized_text = recognize_speech(wav_path)

                            messages.append(
                                f"{timestamp} {NAME} - [Голосовое сообщение] {recognized_text}"
                            )

                            os.remove(wav_path)  # Удаляем временный .wav файл

                            print(
                                f"{timestamp} - [Голосовое сообщение] {recognized_text}"
                            )

                        except Exception as e:
                            print(
                                f"{timestamp} - [Голосовое сообщение] Ошибка при обработке сообщения: {e}"
                            )

                            messages.append(
                                f"{timestamp} {NAME} - [Голосовое сообщение] Ошибка при обработке сообщения"
                            )

                    else:
                        messages.append(
                            f"{timestamp} {NAME} - [Голосовое сообщение] Файл не найден: {audio_path}"
                        )

                # Проверка на видео сообщение

                video_message = message.find("a", class_="media_video")

                if video_message and "href" in video_message.attrs:
                    video_path = os.path.join(
                        CHAT_EXPORT_DIRECTORY, video_message["href"]
                    )

                    if os.path.exists(video_path):
                        try:
                            audio_path = extract_audio_from_video(video_path)

                            recognized_text = recognize_speech(audio_path)

                            messages.append(
                                f"{timestamp} {NAME} - [Видео сообщение] {recognized_text}"
                            )

                            os.remove(audio_path)  # Удаляем временный аудиофайл

                            print(f"{timestamp} - [Видео сообщение] {recognized_text}")

                        except Exception as e:
                            print(
                                f"{timestamp} - [Видео сообщение] Ошибка при обработке сообщения: {e}"
                            )

                            messages.append(
                                f"{timestamp} {NAME} - [Видео сообщение] Ошибка при обработке сообщения"
                            )

                    else:
                        messages.append(
                            f"{timestamp} {NAME} - [Видео сообщение] Файл не найден: {video_path}"
                        )

    return messages


# Основная функция


def main():
    # Директория с файлами

    output_file = os.path.join(CURRENT_DIRECTORY, "messages", "messages_output.txt")

    # Открываем файл для записи

    with open(output_file, "w", encoding="utf-8") as outfile:
        # Перебираем файлы от message1.html до message999.html

        for i in range(1, 40):
            if i == 1:
                file_name = "messages.html"

            else:
                file_name = f"messages{i}.html"

            file_path = os.path.join(CHAT_EXPORT_DIRECTORY, file_name)

            print(file_path)

            # Проверяем, существует ли файл

            if os.path.exists(file_path):
                print(f"Обработка файла: {file_name}")

                messages = extract_messages_from_file(file_path)

                # Записываем сообщения в файл

                for msg in messages:
                    outfile.write(f"{msg}\n")

            else:
                print(f"Файл {file_name} не существует")

    print(f"Результат сохранен в файл: {output_file}")


if __name__ == "__main__":
    main()
