import os
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
from starlette.status import HTTP_403_FORBIDDEN
from conf import r
import json
import redis
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

def get_remaining_quota(api_key: str) -> bool:
    search_res = r.ft("service_UserIDX").search(api_key)
    user_info = json.loads(search_res.docs[0].json)
    return user_info["quota"]

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

