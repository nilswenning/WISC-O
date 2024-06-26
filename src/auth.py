import os
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
from starlette.status import HTTP_403_FORBIDDEN
from conf import r
import json
import redis
import bcrypt
from redis.commands.json.path import Path
from redis.commands.search.query import  Query
import logging
import models

# Load the logging configuration
logger = logging.getLogger(__name__)

API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def is_key_valid(api_key: str) -> bool:
    # check if api key is in redis databse
    try:
        search_res = r.ft("service_UserIDX").search(api_key)
    except redis.exceptions.ResponseError as e:
        return False
    if search_res.total == 0:
        return False
    return True

def get_remaining_quota(api_key: str) -> int:
    search_res = r.ft("service_UserIDX").search(api_key)
    user_info = json.loads(search_res.docs[0].json)
    return int(user_info["quota"])

def get_user_name(api_key: str) -> str:
    search_res = r.ft("service_UserIDX").search(api_key)
    user_info = json.loads(search_res.docs[0].json)
    return user_info["name"]

def decrease_quota(user_name: str, quota: int):
    try:
        search_res = r.ft("service_UserIDX").search(user_name)
        user_info = json.loads(search_res.docs[0].json)
        # if role is admin do not decrease quota
        if not json.loads(search_res.docs[0].json)["role"] == "admin":
            user_info["quota"] -= quota
        user_info["used_minutes"] += quota
        r.json().set(search_res.docs[0].id, Path.root_path(), user_info)
    except Exception as e:
        logging.exception(e)

async def get_api_key(
        api_key_header: str = Security(api_key_header),
):
    if is_key_valid(api_key_header):
        return api_key_header
    else:
        raise HTTPException(status_code=403)


def check_password(user_id, password):
    user_info = r.json().get(user_id)
    hashed_password = user_info["password"].encode('utf-8')

    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def get_api_key_from_username(user_id, password):
    user_info = r.json().get(user_id)
    if check_password(user_id,password):
        return user_info["api_key"]
    else:
        return False

def get_user_info(api_key: str) -> dict:
    """Get the user information from the database using the API key."""
    user_name = get_user_name(str(api_key))
    user_info = r.json().get("wisco:user:" + user_name)
    return user_info


def get_jobs_from_user(user_name: str) -> list:
    """Get all jobs from a user."""
    q = Query("@user:" + user_name + "*").sort_by("created_at", asc=False)  # Use asc=True for ascending order
    # Execute the search using the defined index
    search_res = r.ft("service_idIDX").search(q)
    jobs = []
    for doc in search_res.docs:
        user_job = models.JobInfo()
        user_job.from_dict(json.loads(doc.json))
        jobs.append(user_job)
    return jobs


def create_user(user: models.UserInfo):
    """Create a new user in the database."""
    r.json().set("wisco:user:" + user.name, Path.root_path(), user.to_dict())

if __name__ == "__main__":
    print(get_jobs_from_user("admin"))