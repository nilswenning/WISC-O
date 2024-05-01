import logging
logger = logging.getLogger(__name__)

from datetime import datetime
import os
import json
from rq import Queue
import redis
from redis.commands.json.path import Path
import requests
from conf import upload_folder ,download_folder
from conf import r, Queue
import utils
import time
import auth
import base64

from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)



def add_id(job_id, service_id):
    data = r.json().get(job_id, Path.root_path())
    data['service_id']  = service_id
    r.json().set(str(job_id), Path.root_path(), data)

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
    params = {
        'webhook_id': webhook_id,
        'language': 'german',
    }
    if settings["accuracy"] == "high":
        params['model'] = 'large-v2'
    if settings["accuracy"] == "medium":
        params['model'] = 'small'
    if settings["accuracy"] == "low":
        params['model'] = 'tiny'
    if "language" in settings:
        params['language'] = settings["language"]
    try:
        with open(os.path.join(upload_folder,"audio", jobInfo['newFileName']), 'rb') as file:
            data = file.read()
    except Exception as e:
        logger.exception(e)
    jojo_response = None
    try:
        jojoBaseUrl = os.environ.get("JOJO_BASE_URL")
        jojo_response = requests.post(f'{jojoBaseUrl}/v1/transcribe', params=params, headers=headers, data=data)
        service_id = "JOJO01." + str(jojo_response.json()['job_id']) # use . so redis search dosnt get confused
        add_id(wisco_id, service_id)
        logger.info(f"Processing job: Sended to JOJO with id {service_id}")
    except Exception as e:
        set_job_failed(wisco_id, f"Error in transcribing audio with JOJO: {jojo_response}")
        logger.error(f"Error processing job: {jobInfo['oldFileName']}")
        logger.exception(e)

def transcribe_OpenAi(wisco_id: str, jobInfo: dict):
    try:
        # Open the audio file in read-binary mode
        with open(os.path.join(upload_folder,"audio", jobInfo['newFileName']), 'rb') as audio_file:
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
            summarize(wisco_id)
    except Exception as e:
        set_job_failed(wisco_id, "Error in transcribing text")
        logger.exception(e)
        logger.error(f"Error transcribing file: {jobInfo['oldFileName']}")

def parse_job(settings: str,user_name , oldfileName, newFileName,length, r, status="audio", yt_url=None):
    jobInfos = {
        "user": user_name,
        "oldFileName": oldfileName,
        "newFileName": newFileName,
        "settings": json.loads(settings),
        "length": length,
        "yt_url": yt_url,
        "created_at": utils.get_time_since_epoch_as_str(),
        "finished_at": "",
        "status": status,
        "error": ""
    }
    return jobInfos


def create_job_info(job_info: dict, r: redis.Redis, queue: Queue):
    wisco_id = "wisco:job:" + job_info['newFileName'].split(".")[0] # wisco_id consists of "wisco:job:" + random str
    logger.debug(f"Try To Create job: {wisco_id}")

    try:
        r.json().set(str(wisco_id), Path.root_path(), job_info)
    except Exception as e:
        logger.exception(e)
    logger.info(f"Job Created with id: '{wisco_id}'")
    return wisco_id

def dl_video(url, file_name,new_filename , new_filename_stripped, wisco_job_id, job_info):
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




def start_transcription(wisco_id, job_info):
    settings = job_info['settings']
    if settings["speed"] == "slow":
        try:
            # TODO Change to Queue
            # queue.enqueue(trascibe_jojo,wisco_id, job_info)
            trascibe_jojo(wisco_id, job_info)
            logger.info(f"'{wisco_id}' Summarize started with JOJO")
        except Exception as e:
            logger.exception(e)
    if settings["speed"] == "fast":
        try:
            transcribe_OpenAi(wisco_id, job_info)
        except Exception as e:
            logger.exception(e)

def download_txt(service, job_id,url, wisco_id):
    url = url + "?output=txt"
    jojo_auth = f"{os.environ.get('JOJO_AUTH_USER')}:{os.environ.get('JOJO_AUTH_PASSWORD')}"
    auth_base64 = base64.b64encode(jojo_auth.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_base64}'
    }
    response = requests.get(url, headers=headers)
    file_name = os.path.join(download_folder, "transcriptions", wisco_id.split(":")[-1])+ ".txt"
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w') as file:
        file.write(response.text)

def change_key(wisco_id,key, value):
    job_infos = r.json().get(wisco_id, Path.root_path())
    job_infos[key] = value
    r.json().set(wisco_id, Path.root_path(), job_infos)

def get_key(wisco_id,key):
    job_infos = r.json().get(wisco_id, Path.root_path())
    return job_infos[key]

def set_job_failed(wisco_id, error_msg):
    change_key(wisco_id, "status", "failed")
    change_key(wisco_id, "error", error_msg)
    change_key(wisco_id, "finished_at", utils.get_time_since_epoch_as_str())

def exec_transcription_done(wisco_id, payload):
    if payload.source == "waas":
        download_txt(payload.source, payload.job_id, payload.url, wisco_id)
        change_key(wisco_id,"status","text")
        summarize(wisco_id)


def openai_summaize(system_prompt,user_prompt, text ,wisco_id):
    logger.info(f"Try to summarise text with id: {wisco_id}")
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
    openai_resp_cont = openai_resp.choices[0].message.content
    if "::" in openai_resp_cont:
        file_name = os.path.join(download_folder, "summaries", wisco_id.split(":")[-1])+ ".txt"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w') as file:
            file.write(openai_resp_cont)
        change_key(wisco_id,"status","summarised")
        logger.info("Text Summariesed Successfully with id: {wisco_id}")
    else:
        set_job_failed(wisco_id, "Error in summarising text - GPT Response Error")
    # Create Md
    create_md(wisco_id)

def summarize(wisco_id):
    with open(os.path.join(download_folder, "transcriptions", wisco_id.split(":")[-1] + ".txt"), 'r') as file:
        transcript_text = file.read()

    # TODO insert localisation Here
    system_prompt = "Du fasst Transkripte zusammen. Da Fehler beim transkribieren passieren können, ist es wichtig, dass du eventuelle Logik Fehler korrigierst."
    user_prompt = (
        "wichtig: Gebe die Sektionen mit :: :: eins zu eins wieder"
        "::title::\n"
        "Fasse den Titel hier kurz zusammen und füge einen Zeilenumbruch ein.\n\n"
        "::content::\n"
        "Fasse den Haupttext hier sehr ausführlich zusammen. Achte darauf, keine wichtigen Informationen wegzulassen. "
        "Formatiere den Text angemessen und füge danach einen Zeilenumbruch ein.\n\n"
        "::list::\n"
        "Fasse den gesamten Text hier in einer Liste mit Stichpunkten zusammen. Schreibe dann in der nächsten Zeile.\n\n"
        "::stitle::\n"
        "Fasse den gesamten Text hier in maximal zwei Wörtern zusammen."
    )
    openai_summaize(system_prompt, user_prompt,str(transcript_text),wisco_id)


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
    file_name = os.path.join(download_folder, "md-files",  f"{date_str}-{s_title}.md")
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w') as file:
        file.write(md)
    change_key(wisco_id, "status", "summary-saved")
    change_key(wisco_id, "summary_file_name", f"{date_str}-{s_title}.md")
    change_key(wisco_id, "finished_at", utils.get_time_since_epoch_as_str())
    # if all went well the quota is reduced by the munites of the audio file
    user = get_key(wisco_id, "user")
    auth.decrease_quota(user, get_key(wisco_id, "length"))
    logger.info(f"MD file created with id: {wisco_id} \n all done :)")

