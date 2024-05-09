import os
import redis
from rq import Queue
# Redis Config

if os.getenv('redis_host') is not None:
    redis_host = os.getenv('redis_host')
else:
    redis_host = 'localhost'

r = redis.Redis(host=redis_host, port=6379)
queue = Queue(connection=r)


# Path Config
upload_folder = os.path.join("..", "uploads")
download_folder = os.path.join("..", "downloads")
log_directory = '../logs'

# GPT Config
if os.getenv('gpt_model') is not None:
    gpt_model = os.getenv('gpt_model')
else:
    gpt_model = "gpt-3.5-turbo-0125"
# Fallback model
gpt_fallback_model = "gpt-4-turbo"


# Transcription Config
supported_languages = ["english", "german"]

# Other Config
number_of_retries = 3
download_file_extension = ".srt"


