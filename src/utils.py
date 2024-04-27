import logging
import zipfile

import redis
import random
import string
from pydantic import BaseModel
import os.path
import youtube_dl
import datetime
import pytz # for timezones
from pydub import AudioSegment
import math
from conf import download_folder


class WebhookPayload(BaseModel):
    source: str
    job_id: str
    success: bool
    url: str
    filename: str


def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def createFileName(ext, r):
    # TODO add check if filename is aready created
    return get_random_string(15) + f".{ext}"


def sanitize_filename(filename):
    # Whitelist of allowed characters
    whitelist = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_öüäß"

    # Include only characters that are in the whitelist
    sanitized_filename = ''.join(char for char in filename if char in whitelist)

    return sanitized_filename

def remove_newlines(s):
    # Remove any newline characters from each string in the array
    return s.replace('\n', '')


def get_video_infos(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'force_generic_extractor': True,
        'extract_flat': True,
        'nocheckcertificate': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', None)
        duration = info_dict.get('duration', None)
        return title, duration

def download_video_as_mp3(url,new_filename ):
    options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'postprocessor_args': [
            '-ar', '16000'
        ],
        'prefer_ffmpeg': True,
        'nocheckcertificate': True,
        'keepvideo': False,
        'outtmpl': os.path.join(os.path.join("..", "uploads", "audio"), new_filename + '.%(ext)s')  # Specify the output path here
    }

    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download([url])


def get_time_local_zone_in(seconds):
    # Current time in UTC
    now_utc = datetime.datetime.now(datetime)

    # Add 10 seconds to the local time
    scheduled_time = now_utc + datetime.timedelta(seconds=10)
    # Convert back to UTC as RQ works in UTC
    return scheduled_time


def get_audio_length(file_path):
    audio = AudioSegment.from_file(file_path)
    length_minutes = len(audio) / 1000 / 60
    return math.ceil(length_minutes)


def zipSummaries(fileNames, user_name):
    # Create a new zip file
    zip_file_name = f"summaries_{user_name}.zip"
    folder = os.path.join(download_folder, "zips")
    os.makedirs(folder, exist_ok=True)  # Ensure the directory exists

    zip_path = os.path.join(folder, zip_file_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        # Directory where the files to be zipped are stored
        source_folder = os.path.join(download_folder, "md-files")

        for fileName in fileNames:
            file_path = os.path.join(source_folder, fileName)
            if os.path.exists(file_path):  # Check if the file exists
                # Add the file to the zip file, use relative path for readability
                zipf.write(file_path, arcname=fileName)
            else:
                logging.error(f"Error: The file {fileName} does not exist and will not be added to the ZIP.")

    return zip_file_name



