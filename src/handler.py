import logging

logger = logging.getLogger(__name__)

from datetime import datetime
import os
import json
import redis
from redis.commands.json.path import Path
import requests
from conf import upload_folder, download_folder ,number_of_retries
from conf import r, queue
from rq import Queue
import utils
import models
import auth
from prompts import prompts
import base64

from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


# Handler Entry Point
def start_transcription(wisco_id, job_info):
    settings = job_info['settings']
    if settings["server"] == "JOJO" or settings["server"] == "waasX":
        try:
            queue.enqueue(trascibe_jojo, wisco_id, job_info)
            logger.info(f"'{wisco_id}' Summarize started with JOJO")
        except Exception as e:
            logger.exception(e)
    if settings["server"] == "OpenAI":
        try:
            queue.enqueue(exec_OpenAI_flow, wisco_id, job_info)
        except Exception as e:
            logger.exception(e)


# Workflows
def exec_JOJO_flow(wisco_id, payload):
    if payload.source == "waas" or payload.source == "waasX":
        try:
            download_txt(payload.source, payload.job_id, payload.url, wisco_id)
            exec_combined_flow(wisco_id)
        except Exception as e:
            logger.exception(e)


def exec_OpenAI_flow(wisco_id, job_info):
    try:
        transcribe_OpenAi(wisco_id, job_info)
        exec_combined_flow(wisco_id)
    except Exception as e:
        logger.exception(e)


def exec_combined_flow(wisco_id):
    if get_key(wisco_id, "retry") < number_of_retries:
        try:
            summarize(wisco_id)
            create_md(wisco_id)
        except Exception as e:
            logger.error(f"Error in processing job: {wisco_id} retrying")
            logger.exception(e)
            change_key(wisco_id, "retry", get_key(wisco_id, "retry") + 1)
            queue.enqueue(exec_combined_flow, wisco_id)
    else:
        change_key(wisco_id, "no_more_retry", True)
        change_key(wisco_id, "finished_at", utils.get_epoch_time())
        logger.error(f"Max Retries reached for job: {wisco_id}")


#Downloader
def dl_video(url, file_name, new_filename, new_filename_stripped, wisco_job_id, job_info):
    try:
        folder = os.path.join(upload_folder, "audio")
        os.makedirs(folder, exist_ok=True)
        logger.debug(f"Downloading file: {new_filename}")
        utils.download_video_as_mp3(url, new_filename_stripped)
        logger.info(f"Video: {file_name} Job: {wisco_job_id} downloaded")
        change_key(wisco_job_id, "status", "audio")
        start_transcription(wisco_job_id, job_info)
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error downloading file: {new_filename}")


def download_txt(service, job_id, url, wisco_id):
    url = url + "?output=txt"
    jojo_auth = f"{os.environ.get('JOJO_AUTH_USER')}:{os.environ.get('JOJO_AUTH_PASSWORD')}"
    auth_base64 = base64.b64encode(jojo_auth.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_base64}'
    }
    try:
        response = requests.get(url, headers=headers)
        file_name = os.path.join(download_folder, "transcriptions", wisco_id.split(":")[-1]) + ".txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w') as file:
            file.write(response.text)
        change_key(wisco_id, "status", "text")
    except Exception as e:
        set_job_failed(wisco_id, "Error in downloading text")
        logger.exception(e)
        raise e


# Transcription
def trascibe_jojo(wisco_id: str, jobInfo: dict):
    settings = jobInfo['settings']
    logger.info(f"Processing job {jobInfo['oldFileName']}")
    jojo_auth = f"{os.environ.get('JOJO_AUTH_USER')}:{os.environ.get('JOJO_AUTH_PASSWORD')}"
    auth_base64 = base64.b64encode(jojo_auth.encode()).decode()
    headers = {
        'Content-Type': 'application/octet-stream',
        'Authorization': f'Basic {auth_base64}',
    }
    webhook_id = None
    # check if webhook_id is an evirment variable
    if os.environ.get("JOJO_WEBHOOK_ID") is not None:
        webhook_id = os.environ.get("JOJO_WEBHOOK_ID")
    else:
        webhook_id = "WISCO"
    params = {'webhook_id': webhook_id, 'language': 'german', 'model': 'large-v2'}
    if "accuracy" in settings:
        if settings["accuracy"] == "high":
            params['model'] = 'large-v2'
        if settings["accuracy"] == "medium":
            params['model'] = 'small'
        if settings["accuracy"] == "low":
            params['model'] = 'tiny'
    if "language" in settings:
        params['language'] = settings["language"]
    try:
        with open(os.path.join(upload_folder, "audio", jobInfo['newFileName']), 'rb') as file:
            data = file.read()
    except Exception as e:
        logger.exception(e)
        raise e
    jojo_response = None
    try:
        jojo_base_url = ""
        if settings["server"] == "JOJO":
            jojo_base_url = os.environ.get("JOJO_BASE_URL")
        if settings["server"] == "waasX":
            jojo_base_url = os.environ.get("WAASX_BASE_URL")
        jojo_response = requests.post(f'{jojo_base_url}/v1/transcribe', params=params, headers=headers, data=data, timeout=10)
        service_id = "JOJO01." + str(jojo_response.json()['job_id'])  # use . so redis search dosnt get confused
        add_id(wisco_id, service_id)
        logger.info(f"Processing job: Sended to JOJO with id {service_id}")
    except Exception as e:
        # Retry with OpenAI
        settings["server"] = "OpenAI"
        change_key(wisco_id, "settings", settings)
        start_transcription(wisco_id, jobInfo)
        logger.error(f"Error in transcribing audio with JOJO: {jojo_response}")
        set_job_failed(wisco_id, f"Error in transcribing audio with JOJO: {jojo_response}")
        logger.exception(e)
        raise e


def transcribe_OpenAi(wisco_id: str, jobInfo: dict):
    try:
        # Open the audio file in read-binary mode
        with open(os.path.join(upload_folder, "audio", jobInfo['newFileName']), 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            logger.info(f"Transcription for {jobInfo['oldFileName']} done")

            file_name = os.path.join(download_folder, "transcriptions", wisco_id.split(":")[-1]) + ".txt"
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            with open(file_name, "w") as text_file:
                text_file.write(transcription.text)
            change_key(wisco_id, "status", "text")

    except Exception as e:
        set_job_failed(wisco_id, "Error in transcribing text")
        logger.exception(e)
        logger.error(f"Error transcribing file: {jobInfo['oldFileName']}")
        raise e


#Summarization

def summarize(wisco_id):
    try:
        with open(os.path.join(download_folder, "transcriptions", wisco_id.split(":")[-1] + ".txt"), 'r') as file:
            transcript_text = file.read()
    except Exception as e:
        set_job_failed(wisco_id, "Error in reading tanscription Text file")
        logger.exception(e)
        raise e

    # Get Job info
    job_info = r.json().get(wisco_id, Path.root_path())
    language = "german"
    summary_type = "call"
    if "language" in job_info["settings"] or "sum_type" in job_info["settings"]:
        language = job_info["settings"]["language"]
        summary_type = job_info["settings"]["sum_type"]
    system_prompt = prompts[language][summary_type]["short"]["system"]
    user_prompt = prompts[language][summary_type]["short"]["user"]
    try:
        openai_summaize(system_prompt, user_prompt, str(transcript_text), wisco_id)
    except Exception as e:
        logger.exception(e)
        raise e

def openai_summaize(system_prompt, user_prompt, text, wisco_id):
    logger.info(f"Try to summarise text with id: {wisco_id}")
    openai_resp = None
    try:
        openai_resp = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": text},
            ]
        )
    except Exception as e:
        set_job_failed(wisco_id, "Error in summarising text - GPT Error")
        logger.exception(e)
        raise e
    openai_resp_cont = openai_resp.choices[0].message.content
    if "::" in openai_resp_cont:
        file_name = os.path.join(download_folder, "summaries", wisco_id.split(":")[-1]) + ".txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w') as file:
            file.write(openai_resp_cont)
        change_key(wisco_id, "status", "summarised")
        logger.info("Text Summariesed Successfully with id: {wisco_id}")
    else:
        file_name = os.path.join(download_folder, "failed-summaries", wisco_id.split(":")[-1]) + ".txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w') as file:
            file.write(openai_resp_cont)
        set_job_failed(wisco_id, "Error in summarising text - GPT Response Error")
        logger.error("Error in summarising text - GPT Response Error")
        raise Exception("Error in summarising text - GPT Response Error")


#MD Creation


def create_md(wisco_id):
    logging.info("Create MD with id: {wisco_id}")
    with open(os.path.join(download_folder, "summaries", wisco_id.split(":")[-1] + ".txt"), 'r') as file:
        summary_text = file.read()
    parts = summary_text.split("::")
    title = parts[2]
    content = parts[4]
    list = parts[6]
    s_title = parts[8]
    title = utils.remove_newlines(title)
    s_title = utils.sanitize_filename(s_title)
    # TODO insert localisation Here
    md = f"# {title}\n## Kurze Zusammenfassung:\n{list}\n\n{content}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_name = os.path.join(download_folder, "md-files", f"{date_str}-{s_title}.md")
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w') as file:
        file.write(md)
    change_key(wisco_id, "status", "summary-saved")
    change_key(wisco_id, "summary_file_name", f"{date_str}-{s_title}.md")
    change_key(wisco_id, "finished_at", utils.get_epoch_time())
    # if all went well the quota is reduced by the munites of the audio file
    user = get_key(wisco_id, "user")
    auth.decrease_quota(user, get_key(wisco_id, "length"))
    logger.info(f"MD file created with id: {wisco_id} \n all done :)")


#Utils

def add_id(job_id, service_id):
    data = r.json().get(job_id, Path.root_path())
    data['service_id'] = service_id
    r.json().set(str(job_id), Path.root_path(), data)


def parse_job(settings: str, user_name, oldfileName, newFileName, length, status="audio", yt_url=None):
    job_infos = models.JobInfo(user_name, oldfileName, newFileName, settings, length, yt_url, status)
    return job_infos.to_dict()


def create_job_info(job_info: dict, r: redis.Redis, queue: Queue):
    stripped_id = job_info['newFileName'].split(".")[0]
    wisco_id = "wisco:job:" + stripped_id  # wisco_id consists of "wisco:job:" + random str
    logger.debug(f"Try To Create job: {wisco_id}")
    job_info["id"] = stripped_id
    try:
        r.json().set(str(wisco_id), Path.root_path(), job_info)
    except Exception as e:
        logger.exception(e)
    logger.info(f"Job Created with id: '{wisco_id}'")
    return wisco_id


def change_key(wisco_id, key, value):
    job_infos = r.json().get(wisco_id, Path.root_path())
    job_infos[key] = value
    r.json().set(wisco_id, Path.root_path(), job_infos)


def get_key(wisco_id, key):
    job_infos = r.json().get(wisco_id, Path.root_path())
    return job_infos[key]


def set_job_failed(wisco_id, error_msg):
    change_key(wisco_id, "status", "failed")
    change_key(wisco_id, "error", error_msg)
    change_key(wisco_id, "finished_at", utils.get_epoch_time())
