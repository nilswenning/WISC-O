import json
import os
from datetime import datetime
import utils  # assuming utils module exists with get_epoch_time_as_string function


class WiscoModel():
    def to_dict(self):
        return self.__dict__

    def to_json(self):
        return json.dumps(self.__dict__)

    def from_dict(self, dict):
        for key, value in dict.items():
            setattr(self, key, value)

    def from_json(self, json_str):
        self.from_dict(json.loads(json_str))


class ApiResponse(WiscoModel):
    def __init__(self, status="fail", message="", raw=""):
        self.status = status
        self.message = message
        self.raw = raw


class JobInfo(WiscoModel):
    def __init__(self, user=None, oldFileName=None, newFileName=None, settings=None, length=None, yt_url=None,
                 status=None, wisco_id=None):
        self.id = wisco_id
        self.user = user
        self.oldFileName = oldFileName
        self.newFileName = newFileName
        self.settings = json.loads(settings) if settings is not None else None
        self.length = length
        self.yt_url = yt_url
        self.created_at = utils.get_epoch_time()
        self.finished_at = 0
        self.downloaded = False
        self.status = status
        self.retry = 0
        self.no_more_retry = False
        self.error = ""
        self.service_id = ""
        self.summary_file_name = ""


class UserInfo(WiscoModel):
    def __init__(self, name, role, email, password, api_key=None):
        if api_key is None:
            api_key = utils.generate_random_string(12)
        self.name = name
        self.role = role
        self.email = email
        self.password = utils.hash_password(password)
        self.api_key = api_key
        self.quota = 600
        self.created_at = utils.get_epoch_time()
        self.used_minutes = 0


class JobResult(WiscoModel):
    def __init__(self, transcribed_text=None, summary_text=None):
        self.transcribed_text = transcribed_text
        self.summary_text = summary_text

class ServerOptions(WiscoModel):
    def __init__(self, languages=None, summary_prompts=None):
        self.server = []
        if "WAASX_BASE_URL" in os.environ and utils.check_waasX_avail(timeout=1):
            self.server.append("waasX")
        self.server.append("OpenAI")
        if "JOJO_BASE_URL" in os.environ:
            self.server.append("JOJO")
        self.languages = languages
        self.summary_prompts = summary_prompts
