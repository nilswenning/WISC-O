import json
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
