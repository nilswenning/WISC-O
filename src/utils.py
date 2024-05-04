import logging
import zipfile
import redis
import random
import string
import os
import youtube_dl
import datetime
import pytz  # for timezones
from pydantic import BaseModel
from pydub import AudioSegment
import math
import bcrypt
from conf import r
from conf import download_folder
import auth
import redis
from redis.commands.json.path import Path
import redis.commands.search.aggregation as aggregations
import redis.commands.search.reducers as reducers
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import NumericFilter, Query


def init_db():
    try:
        schema_jobId = (TextField("$.service_id", as_name="service_id"), TextField("$.user", as_name="user"),
                        TextField("$.yt_url", as_name="yt_url"))
        r.ft("service_idIDX").create_index(schema_jobId,
                                           definition=IndexDefinition(prefix=["wisco:job:"], index_type=IndexType.JSON))
    except redis.exceptions.ResponseError as e:
        None
    try:
        schema_User = (TextField("$.api_key", as_name="apikey"), TextField("$.name", as_name="name"),
                       TextField("$.role", as_name="role"))
        r.ft("service_UserIDX").create_index(schema_User, definition=IndexDefinition(prefix=["wisco:user:"],
                                                                                     index_type=IndexType.JSON))
    except redis.exceptions.ResponseError as e:
        None

    # Init Admin User
    wisco_user_id = "wisco:user:admin"
    wisco_user = {
        "name": "admin",
        "role": "admin",  # admin or user can create other users
        "email": os.getenv("admin_email"),
        "password": os.getenv("admin_password"),
        "api_key": os.getenv("admin_api_key"),
        "quota": 10000,
    }
    try:
        auth.updateUser(wisco_user_id, wisco_user)
    except redis.exceptions.ResponseError as e:
        None


class WebhookPayload(BaseModel):
    """Model representing the payload received from a webhook."""
    source: str
    job_id: str
    success: bool
    url: str
    filename: str


def generate_random_string(length: int) -> str:
    """Generate a random string of specified length using lowercase letters."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


def create_filename(extension: str) -> str:
    """Create a random filename with the given extension."""
    return generate_random_string(15) + f".{extension}"


def sanitize_filename(filename: str) -> str:
    """Remove unwanted characters from the filename."""
    whitelist = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_öüäß")
    return ''.join(char for char in filename if char in whitelist)


def remove_newlines(text: str) -> str:
    """Remove newline characters from a string."""
    return text.replace('\n', '')


def extract_video_info(url: str) -> tuple:
    """Extract the title and duration of a video from a given URL."""
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
        return info_dict.get('title'), info_dict.get('duration')


def download_video_as_mp3(url: str, filename: str) -> None:
    """Download the audio of a video as an MP3 file with the specified filename."""
    options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'postprocessor_args': ['-ar', '16000'],
        'prefer_ffmpeg': True,
        'nocheckcertificate': True,
        'keepvideo': False,
        'outtmpl': os.path.join("..", "uploads", "audio", f"{filename}.%(ext)s")
    }

    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download([url])


def get_scheduled_time_in_seconds(seconds: int) -> datetime.datetime:
    """Get the time in UTC with an offset of specified seconds."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return now_utc + datetime.timedelta(seconds=seconds)


def get_audio_length_in_minutes(file_path: str) -> int:
    """Get the length of an audio file in minutes, rounded up."""
    audio = AudioSegment.from_file(file_path)
    length_minutes = len(audio) / 1000 / 60
    return math.ceil(length_minutes)


def create_summary_zip(file_names: list, user_name: str) -> str:
    """Create a zip file containing the specified files for a user."""
    zip_file_name = f"summaries_{user_name}.zip"
    folder = os.path.join(download_folder, "zips")
    os.makedirs(folder, exist_ok=True)

    zip_path = os.path.join(folder, zip_file_name)
    source_folder = os.path.join(download_folder, "md-files")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_name in file_names:
            file_path = os.path.join(source_folder, file_name)
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=file_name)
            else:
                logging.error(f"Error: The file {file_name} does not exist and will not be added to the ZIP.")

    return zip_file_name


def get_epoch_time_as_string() -> str:
    """Get the current time since epoch as a string."""
    return str(round(datetime.datetime.now().timestamp()))
