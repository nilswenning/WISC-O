# Import Logging

import logging.config
import math
# import base Stuff
import os
import json
import datetime


from conf import upload_folder, r, queue, download_folder, log_directory, download_file_extension, supported_languages
from redis.commands.search.query import NumericFilter, Query

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Load the logging configuration
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

# Import Fastapi Stuff
from typing import Annotated, List, Optional
from fastapi.security.api_key import APIKey
from fastapi import FastAPI, Form, File, UploadFile, Depends
from fastapi.responses import FileResponse


# Import Own stuff
import handler
import utils
import auth
import models
from prompts import prompts



# Log Start
logger.info('Starting API')

# Init db
utils.init_db()

if os.getenv("WAASX_BASE_URL") is not None:
    utils.save_waasX_state_to_db()


app = FastAPI()


@app.post("/v1/createDlJob")
async def create_file_dl(
        url: Annotated[str, Form()],
        settings: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    return handler.handle_yt_link(url, settings, api_key)


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
            new_filename = utils.create_filename(extension)
            logger.debug(f"writing file: {new_filename}")
            folder = os.path.join(upload_folder, "audio")
            os.makedirs(folder, exist_ok=True)

            if file.filename == "watch":
                data = file.file.read(5000)
                url = utils.extract_url(data)
                if url is None:
                    response = models.ApiResponse("fail", "No URL found in the file")
                    return response.to_dict()
                handler.handle_yt_link(url, settings, api_key)
            elif extension in ["mp3", "wav", "flac", "m4a"]:
                try:
                    extension = os.path.splitext(file.filename)[1]
                    if extension == ".mp3":

                        with open(os.path.join(folder, new_filename), 'wb') as f:
                            while contents := file.file.read(1024 * 1024):
                                f.write(contents)

                        audo_length = utils.get_audio_length_in_minutes(os.path.join(folder, new_filename))
                        if audo_length > auth.get_remaining_quota(str(api_key)):
                            quota = auth.get_remaining_quota(str(api_key))
                            response = models.ApiResponse("fail", f"Your audio is too long. You have only {quota} minutes left and the audio is {audo_length} minutes long")
                            return response.to_dict()

                        job_info = handler.parse_job(settings, auth.get_user_name(str(api_key)), file.filename, new_filename, audo_length)
                        wisco_job_id = handler.create_job_info(job_info, r, queue)
                        handler.start_transcription(wisco_job_id, job_info)
                except Exception as e:
                    logger.exception(e)
                    response = models.ApiResponse("fail", f"Error processing file: {file.filename}")
                    return response.to_dict()
                finally:
                    file.file.close()
                response = models.ApiResponse("success", f"Your Job was created with the ID: {wisco_job_id}")
                return response.to_dict()
            else:
                logger.info(f"File extension not supported: {extension} coming from file: {file.filename}")
                response = models.ApiResponse("fail", "File extension not supported")
                return response.to_dict()
        except Exception as e:
            logger.exception(e)
            response = models.ApiResponse("fail", f"Error processing file: {file.filename}")
            return response.to_dict()











#
@app.post("/webhook/", response_model=dict, summary="Receive webhook",
          description="Receives a webhook POST request with an ID and a message.")
async def receive_webhook(payload: utils.WebhookPayload):
    logger.info(f"Received webhook payload: {payload}")
    try:
        if payload.source == "waas" or payload.source == "waasX":
            wisco_id = ""
            if payload.success:
                try:
                    q = Query("@service_id:" + payload.job_id.split("-")[-1])
                    # Execute the search using the defined index
                    search_res = r.ft("service_idIDX").search(q)
                    wisco_id = search_res.docs[0].id
                    # Must be done in a queue but 10 seconds later because the file is not ready ye
                    logger.info(f"transcription done for {wisco_id}")
                    wait_time = 10
                    if payload.source == "waasX":
                        wait_time = 0
                    job = queue.enqueue_in(datetime.timedelta(seconds=wait_time), handler.exec_JOJO_flow, args=(wisco_id, payload))

                    # handler.exec_transcription_done(wisco_id, payload)
                except Exception as e:
                    logger.exception(e)
            else:
                job_infos = r.json().get(wisco_id)
                settings = models.Settings()
                settings = settings.from_dict(job_infos["settings"])
                settings["server"] = "OpenAI"
                handler.change_key(wisco_id, "settings", settings.to_dict())
                handler.change_key(wisco_id, "status", "audio")
                handler.start_transcription(wisco_id, job_infos)
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
        zip_file_name = utils.create_summary_zip(file_names, user)
        return {"message": f"Zip file created: {zip_file_name}", "zip_file_name": zip_file_name}
    except Exception as e:
        logger.exception(e)
        return {"message": "There was an error getting the files"}

# User specific routes


@app.post("/v1/getJobResult")
async def get_job_result(
        jobid: Annotated[str, Form()],
        api_key: APIKey = Depends (auth.get_api_key)):
    try:
        job_info = r.json().get("wisco:job:" + jobid)
        if not job_info:
            response = models.ApiResponse("fail", "Job not found")
            return response.to_dict()
        if not job_info['user'] == auth.get_user_name(str(api_key)):
            response = models.ApiResponse("fail", "You are not allowed to get this job")
            return response.to_dict()
        # Get Transcription and Summary
        # check if file is created with os
        transcription = ""
        summary = ""
        if os.path.exists(os.path.join(download_folder, "transcriptions", job_info["newFileName"].split(".")[0] + download_file_extension)):
            with open(os.path.join(download_folder, "transcriptions", job_info["newFileName"].split(".")[0] + download_file_extension), 'r') as f:
                transcription = f.read()
        if os.path.exists(os.path.join(download_folder, "md-files",  job_info["summary_file_name"])) and job_info["summary_file_name"] != "":
            with open(os.path.join(download_folder, "md-files", job_info["summary_file_name"]), 'r') as f:
                summary = f.read()

        # Base64 encode the files
        transcription = utils.base64_encode_string(transcription)
        summary = utils.base64_encode_string(summary)
        job_result = models.JobResult(transcribed_text=transcription, summary_text=summary)
        response = models.ApiResponse("success", "Job result retrieved successfully", raw=job_result)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        api_response = models.ApiResponse("fail", "There was an error getting the job")
        return api_response.to_dict()

@app.post("/v1/getApiKey")
async def get_api_key(
        username: Annotated[str, Form()],
        password: Annotated[str, Form()]):
    try:
        wisco_username = f"wisco:user:{username}"
        if r.exists(wisco_username) == 0:
            response = models.ApiResponse("fail", f"User {username} not found")
            return response.to_dict()
        user_api_key = auth.get_api_key_from_username(wisco_username, password)
        if user_api_key is not False:
            response = models.ApiResponse("success", f"Your API Key is {user_api_key}",raw=user_api_key)
            return response.to_dict()
        else:
            response = models.ApiResponse("fail", "Password is incorrect")
            return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = models.ApiResponse("fail", "There was an error getting the API Key")
        return response.to_dict()
@app.post("/v1/getUserInfo")
async def get_user_info(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        user_info = auth.get_user_info(str(api_key))
        user_info["password"] = "*********" # hide password
        response = models.ApiResponse("success", f"Your user info is {user_info}", raw=user_info)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = models.ApiResponse("fail", "There was an error getting the user info")
        return response.to_dict()



@app.post("/v1/getQuota")
async def get_quota(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        quota = auth.get_remaining_quota(str(api_key))
        response = models.ApiResponse("success", f"Your quota is {quota}", raw=quota)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = models.ApiResponse("fail", "There was an error getting the quota")
        return response.to_dict()


@app.post("/v1/resummarize")
async def resummarize(
        jobid: Annotated[str, Form()],
        settings: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        settings_str = settings
        #check if user is allowed to resummarize
        wisco_id = "wisco:job:" + jobid
        job_info = r.json().get(wisco_id)
        if not job_info:
            response = models.ApiResponse("fail", "Job not found")
            return response.to_dict()
        if not job_info['user'] == auth.get_user_name(str(api_key)):
            response = models.ApiResponse("fail", "You are not allowed to resummarize this job")
            return response.to_dict()
        if not (job_info['status'] == "summary-saved" or  job_info['status'] == "failed"):
            response = models.ApiResponse("fail", "The file is not ready yet")
            return response.to_dict()
        # Dont change the server setting
        settings = models.Settings()
        settings.from_json(settings_str)
        handler.change_key(wisco_id, "settings", settings.to_dict())
        handler.change_key(wisco_id, "status", "text")
        handler.change_key(wisco_id, "retry", 0)
        queue.enqueue(handler.exec_combined_flow, wisco_id)
        response = models.ApiResponse("success", f"Your Job was resummarized with the ID: {wisco_id}")
        logger.info(f"Job {wisco_id} queued to be resummarized")
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = models.ApiResponse("fail", "There was an error resummarizing the job")
        return response.to_dict()

@app.post("/v1/restartJob")
async def restart_job(
        jobid: Annotated[str, Form()],
        settings: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        settings_str = settings
        # check if user is allowed to resummarize
        wisco_id = "wisco:job:" + jobid
        job_info = r.json().get(wisco_id)
        if not job_info:
            response = models.ApiResponse("fail", "Job not found")
            return response.to_dict()
        if not job_info['user'] == auth.get_user_name(str(api_key)):
            response = models.ApiResponse("fail", "You are not allowed to recreate this job")
            return response.to_dict()
        settings = models.Settings()
        settings.from_json(settings_str)
        handler.change_key(wisco_id, "settings", settings.to_dict())
        handler.change_key(wisco_id, "status", "audio")
        handler.change_key(wisco_id, "retry", 0)
        job_info = r.json().get(wisco_id)
        handler.start_transcription(wisco_id, job_info)
        response = models.ApiResponse("success", f"Your Job was recreated with the ID: {wisco_id}")
        logger.info(f"Job {wisco_id} recreated and queued again")
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = models.ApiResponse("fail", "There was an error while recreating the job")
        return response.to_dict()




@app.post("/v1/getJob")
async def get_job(
        jobid: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        job_info = r.json().get("wisco:job:" + jobid)
        if not job_info:
            response = models.ApiResponse("fail", "Job not found")
            return response.to_dict()
        if not job_info['user'] == auth.get_user_name(str(api_key)):
            response = models.ApiResponse("fail", "You are not allowed to get this job")
            return response.to_dict()
        response = models.ApiResponse("success", "Job retrieved successfully", raw=job_info)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        return {"message": "There was an error getting the jobs"}


@app.post("/v1/getJobs")
async def get_jobs(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        user_name = auth.get_user_name(str(api_key))
        jobs = auth.get_jobs_from_user(user_name)
        api_response = models.ApiResponse("success", "Jobs retrieved successfully", raw=jobs)
        return api_response.to_dict()
    except Exception as e:
        logger.exception(e)
        return {"message": "There was an error getting the jobs"}

# Service specific routes

@app.post("/v1/getServerOptions")
async def get_server_options(
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        languages = list(prompts.keys())
        summary_prompts = list(prompts["english"].keys())
        server_options = models.ServerOptions(languages=languages, summary_prompts=summary_prompts)
        response = models.ApiResponse("success", "Server options retrieved successfully", raw=server_options)
        return response.to_dict()
    except Exception as e:
        logger.exception(e)
        response = models.ApiResponse("fail", "There was an error getting the server options")
        return response.to_dict()

# Admin specific routes
@app.post("/v1/commands")
async def commands(
        command: Annotated[str, Form()],
        api_key: APIKey = Depends(auth.get_api_key)):
    try:
        # Check if user is admin
        user_info = auth.get_user_info(str(api_key))
        if not user_info["role"] == "admin":
            api_response = models.ApiResponse("fail", "You are not allowed to execute this command")
            return api_response.to_dict()
        logger.info(f"Executing command: {command}")
        if command == "FLUSHALL":
            utils.remove_in_folder(upload_folder)
            utils.remove_in_folder(download_folder)
            r.flushall()
            utils.init_db()
            utils.save_waasX_state_to_db()
            api_response = models.ApiResponse("success", "Command executed successfully")
            return api_response.to_dict()
    except Exception as e:
        logger.exception(e)
        return {"message": "There was an error executing the command"}