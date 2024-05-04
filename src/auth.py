import os
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
from starlette.status import HTTP_403_FORBIDDEN
from conf import r
import json
import redis
import bcrypt
from redis.commands.json.path import Path
import logging

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
        # if role is admin do not decrease quota
        if json.loads(search_res.docs[0].json)["role"] == "admin":
            return
        user_info = json.loads(search_res.docs[0].json)
        user_info["quota"] -= quota
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


def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def updateUser(user_id, user_info):
    user_info["password"] = hash_password(user_info["password"])
    r.json().set(user_id, Path.root_path(), user_info)


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
