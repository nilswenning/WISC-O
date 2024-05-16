import logging
import zipfile
import redis
import random
import string
import os
import requests
import youtube_dl
import datetime
import pytz  # for timezones
from pydantic import BaseModel
from pydub import AudioSegment
import math
import shutil
import bcrypt
from conf import r, queue
from conf import download_folder
import auth
import base64
import redis
from redis.commands.json.path import Path
import redis.commands.search.aggregation as aggregations
import redis.commands.search.reducers as reducers
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import NumericFilter, Query
import models
from bs4 import BeautifulSoup


def init_db():
    try:
        schema_jobId = (TextField("$.service_id", as_name="service_id"), TextField("$.user", as_name="user"), NumericField("$.created_at", as_name="created_at"),
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
    admin_user = models.UserInfo("admin", "admin", os.getenv("admin_email"),
                             os.getenv("admin_password"), api_key=os.getenv("admin_api_key"))
    try:
        auth.create_user(admin_user)
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
    """Remove unwanted characters from the filename, replace spaces with underscores, and remove leading non-alphanumeric characters."""
    filename = filename.replace(" ", "_")
    whitelist = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_öüäß")
    sanitized = ''.join(char for char in filename if char in whitelist)
    return sanitized.lstrip('_')


def remove_newlines(text: str) -> str:
    """Remove newline characters from a string."""
    return text.replace('\n', '')


def remove_srt_tags(text: str) -> str:
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        if line.startswith("["):
            new_lines.append(line)
    return "\n".join(new_lines)


def extract_url(html_content):
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the <link> tag with rel="canonical" attribute
    canonical_link = soup.find('link', {'rel': 'canonical'})

    if canonical_link:
        # Extract the value of the "href" attribute
        url = canonical_link.get('href')
        return url
    else:
        return None


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


def get_epoch_time() -> int:
    """Get the current time since epoch as a string."""
    return int(round(datetime.datetime.now().timestamp()))



def remove_in_folder(folder_path):
    """
    Remove all folders and files within the specified folder recursively.

    Parameters:
        folder_path (str): The path to the folder from which folders will be removed.

    Returns:
        None
    """
    # Check if the folder path exists
    if not os.path.exists(folder_path):
        print(f"The folder '{folder_path}' does not exist.")
        return

    # Recursively remove all files and folders within the specified folder
    for root, dirs, files in os.walk(folder_path, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            os.remove(file_path)
            logging.debug(f"Removed file: {file_path}")
        for name in dirs:
            dir_path = os.path.join(root, name)
            shutil.rmtree(dir_path)
            logging.debug(f"Removed directory: {dir_path}")


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def base64_encode_string(string):
    return base64.b64encode(string.encode('utf-8')).decode('utf-8')


def check_waasX_avail(timeout=1):
    url = f"{os.getenv('WAASX_BASE_URL')}/v1/isAvailable"
    username = os.getenv("WAASX_AUTH_USER")
    password = os.getenv("JOJO_AUTH_PASSWORD")
    headers = {'accept': 'application/json'}

    try:
        response = requests.get(url, headers=headers, auth=(username, password), timeout=timeout)
        if response.status_code != 200:
            logging.debug("WAAS-X Server is Not Online")
            return False
        if response.json()["available"]:
            return True
        else:
            return False
    except requests.Timeout:
        logging.debug("WAAS-X Server is Not Online")
        return False
    except requests.RequestException as e:
        logging.exception(e)
        return False
    except Exception as e:
        logging.exception(e)
        return False

def save_waasX_state_to_db():
    if check_waasX_avail(5):
        r.set("waasX:state", "available")
    else:
        r.set("waasX:state", "unavailable")
    queue.enqueue_in(datetime.timedelta(seconds=30), save_waasX_state_to_db)

def get_waasX_state_from_db():
    if r.get("waasX:state") == b"available":
        return True
    else:
        return False