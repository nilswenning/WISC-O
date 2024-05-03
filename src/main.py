# Import Logging

import logging.config
import math
# import base Stuff
import os
import json
import datetime


from conf import upload_folder, r, queue, download_folder, log_directory

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Load the logging configuration
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)






# Redis Stuff

import redis
from redis.commands.json.path import Path
import redis.commands.search.aggregation as aggregations
import redis.commands.search.reducers as reducers
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import NumericFilter, Query

# Import Fastapi Stuff
from typing import Annotated, List, Optional
from fastapi.security.api_key import APIKey
from fastapi import FastAPI, Form, File, UploadFile, Depends
from fastapi.responses import FileResponse


# Import Own stuff
import handler
import utils
import auth
import apiResponses



# Log Start
logger.info('Starting API')

# Init DB
# init indexing DB
try:
    schema_jobId = (TextField("$.service_id", as_name="service_id"), TextField("$.user", as_name="user"), TextField("$.yt_url", as_name="yt_url"))
    r.ft("service_idIDX").create_index(schema_jobId, definition=IndexDefinition(prefix=["wisco:job:"], index_type=IndexType.JSON))
except redis.exceptions.ResponseError as e:
    None
try:
    schema_User = (TextField("$.api_key", as_name="apikey"), TextField("$.name", as_name="name"), TextField("$.role", as_name="role"))
    r.ft("service_UserIDX").create_index(schema_User, definition=IndexDefinition(prefix=["wisco:user:"], index_type=IndexType.JSON))
except redis.exceptions.ResponseError as e:
    None

# Init Admin User
wisco_user_id = "wisco:user:admin"
wisco_user = {
    "name": "admin",
    "role": "admin", # admin or user can create other users
    "email": os.getenv("admin_email"),
    "password": os.getenv("admin_password"),
    "api_key": os.getenv("admin_api_key"),
    "quota": 10000,
}
try:
    auth.updateUser(wisco_user_id, wisco_user)
except redis.exceptions.ResponseError as e:
    None

app = FastAPI()


@app.post("/v1/createDlJob")
async def create_file_dl(
        url: Annotated[str, Form()],
        settings: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)
):


    try:
        file_name, duration = utils.get_video_infos(url)
    except Exception as e:
        logger.exception(e)
        return {"message": f"There was an error getting video Infos"}

    video_minutes = math.ceil(duration/60)
    try:
        if video_minutes > auth.get_remaining_quota(str(api_key)):
            response = apiResponses.ApiResponse("fail", f"Your video is too long. You have only {auth.get_remaining_quota(str(api_key))} minutes left and the video is {video_minutes} minutes long")
            return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = apiResponses.ApiResponse("fail", f"Your video is too long. You have only {auth.get_remaining_quota(str(api_key))} minutes left and the video is {video_minutes} minutes long")
        return response.to_dict()



    logger.info(f"processing YT Video: {file_name}")
    new_filename = utils.createFileName("mp3", r)
    new_filename_stripped = new_filename.split(".")[0]
    job_info = handler.parse_job(settings, auth.get_user_name(str(api_key)), file_name, new_filename, video_minutes, r, status="DL", yt_url=url)
    wisco_job_id = handler.create_job_info(job_info, r, queue)
    logger.info(f"Video: {file_name} connected with Job: {wisco_job_id}")
    try:
        handler.dl_video(url, file_name, new_filename, new_filename_stripped, wisco_job_id, job_info)
        # Answer to the user
        response = apiResponses.ApiResponse("success", f"Your Job was created with the ID: {wisco_job_id}")
        return response.to_dict()
    except Exception as e:
        handler.change_key(wisco_job_id, "status", "DL_ERROR")
        logger.exception(e)
        return {"message": f"There was an error downloading the file"}


# Allows for uploading multiple files
@app.post("/v1/createJob")
async def create_file(
        files: List[UploadFile],
        settings: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):


    for file in files:
        try:
            logger.info(f"processing file: {file.filename}")
            extension = file.filename.split(".")[-1]
            new_filename = utils.createFileName(extension, r)
            logger.debug(f"writing file: {new_filename}")
            folder = os.path.join(upload_folder, "audio")
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, new_filename), 'wb') as f:
                while contents := file.file.read(1024 * 1024):
                    f.write(contents)

            audo_length = utils.get_audio_length(os.path.join(folder, new_filename))
            if audo_length > auth.get_remaining_quota(str(api_key)):
                quota = auth.get_remaining_quota(str(api_key))
                response = apiResponses.ApiResponse("fail", f"Your audio is too long. You have only {quota} minutes left and the audio is {audo_length} minutes long")
                return response.to_dict()

            job_info = handler.parse_job(settings, auth.get_user_name(str(api_key)), file.filename, new_filename, audo_length, r)
            wisco_job_id = handler.create_job_info(job_info, r, queue)
            handler.start_transcription(wisco_job_id, job_info)
        except Exception as e:
            logger.exception(e)
            response = apiResponses.ApiResponse("fail", f"Error processing file: {file.filename}")
            return response.to_dict()
        finally:
            file.file.close()
    response = apiResponses.ApiResponse("success", f"Your Job was created with the ID: {wisco_job_id}")
    return response.to_dict()

# User specific routes

@app.post("/v1/getApiKey")
async def get_api_key(
        username: Annotated[str, Form()],
        password: Annotated[str, Form()]):
    try:
        wisco_username = f"wisco:user:{username}"
        if r.exists(wisco_username) == 0:
            response = apiResponses.ApiResponse("fail", f"User {username} not found")
            return response.to_dict()
        user_api_key = auth.get_api_key_from_username(wisco_username, password)
        if user_api_key is not False:
            response = apiResponses.ApiResponse("success", f"Your API Key is {user_api_key}",raw=user_api_key)
            return response.to_dict()
        else:
            response = apiResponses.ApiResponse("fail", "Password is incorrect")
            return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = apiResponses.ApiResponse("fail", "There was an error getting the API Key")
        return response.to_dict()
@app.post("/v1/getUserInfo")
async def get_user_info(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        user_name = auth.get_user_name(str(api_key))
        user_info = r.json().get("wisco:user:" + user_name)
        user_info["password"] = "*********" # hide password
        response = apiResponses.ApiResponse("success", f"Your user info is {user_info}", raw=user_info)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = apiResponses.ApiResponse("fail", "There was an error getting the user info")
        return response.to_dict()



@app.post("/v1/getQuota")
async def get_quota(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        quota = auth.get_remaining_quota(str(api_key))
        response = apiResponses.ApiResponse("success", f"Your quota is {quota}", raw=quota)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = apiResponses.ApiResponse("fail", "There was an error getting the quota")
        return response.to_dict()


@app.post("/v1/resummarize")
async def resummarize(
        wisco_id: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    # TODO add options
    try:
        handler.summarize(wisco_id)
    except Exception as e:
        logger.exception(e)
    return {"status": "success"}

@app.post("/v1/createMd")
async def create_md_test(
        wisco_id: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    # TODO add options
    try:
        handler.create_md(wisco_id)
    except Exception as e:
        logger.exception(e)
    return {"status": "success"}




@app.post("/webhook/", response_model=dict, summary="Receive webhook",
          description="Receives a webhook POST request with an ID and a message.")
async def receive_webhook(payload: utils.WebhookPayload):
    logger.info(f"Received webhook payload: {payload}")
    try:
        if payload.source == "waas":
            if payload.success:
                try:
                    search_res = r.ft("service_idIDX").search(payload.job_id.split("-")[-1]) # idk why but searching for the whole sting failed -> only last chunck is used
                    wisco_id = search_res.docs[0].id
                    # Must be done in a queue but 10 seconds later because the file is not ready ye

                    job = queue.enqueue_in(datetime.timedelta(seconds=10), handler.exec_transcription_done, args=(wisco_id, payload))

                    # handler.exec_transcription_done(wisco_id, payload)
                except Exception as e:
                    logger.exception(e)
            else:
                None
                # TODO Report Error to user
    except Exception as e:
        logger.exception(e)
    return {"message": "Webhook received successfully!"}


@app.post("/v1/dlSingle")
async def dl_single(
        jobid: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        # Get the job info
        job_info = r.json().get("wisco:job:" + jobid)
        # Check if response is empty
        if not job_info:
            return {"message": "Job not found"}
        # Check if user created the job
        if not job_info['user'] == auth.get_user_name(str(api_key)):
            return {"message": "You are not allowed to download this file"}
        if not job_info['status'] == "summary-saved":
            return {"message": "The file is not ready yet"}
        # Get the file name
        file_name = job_info["summary_file_name"]
        # resopnd with the file
        handler.change_key("wisco:job:" + jobid, "downloaded", True)
        return FileResponse(os.path.join(download_folder, "md-files", file_name), filename=file_name)

    except Exception as e:
        logger.exception(e)


@app.post("/v1/dlZip")
async def dl_Zip(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        zip_file_name = "summaries_" + auth.get_user_name(str(api_key)) + ".zip"
        return FileResponse(os.path.join(download_folder, "zips", zip_file_name), filename=zip_file_name)
    except Exception as e:
        logger.exception(e)
        return {"message": "There was an error getting the files"}

@app.post("/v1/getZipFileName")
async def get_Zip_File_Name(
        settings: Optional[str] = Form(default=None),
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        download_already_downloaded = False
        if settings is not None:
            settings = json.loads(settings)
            if settings["dlOnlyNew"]:
                download_already_downloaded = True

        # Get list of all jobs of the user
        #get user name
        user = auth.get_user_name(str(api_key))
        logger.info("Creating Zip file for user: " + user)
        search_res = r.ft("service_idIDX").search(f"@user:{user}")
        # Check if response is empty
        if not search_res.total:
            return {"message": "No Jobs found"}
        # Get list of file names
        file_names = []
        for doc in search_res.docs:
            job_info = json.loads(doc.json)
            if job_info['status'] == "summary-saved":
                if download_already_downloaded:
                    if 'downloaded' in job_info:
                        if job_info['downloaded']:
                            continue
                file_names.append(job_info["summary_file_name"])
                handler.change_key(doc.id, "downloaded", True)
        if not file_names:
            return {"message": "No new files to download"}
        zip_file_name = utils.zipSummaries(file_names, user)
        return {"message": f"Zip file created: {zip_file_name}", "zip_file_name": zip_file_name}
    except Exception as e:
        logger.exception(e)
        return {"message": "There was an error getting the files"}