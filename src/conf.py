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

# Other Config
number_of_retries = 3
