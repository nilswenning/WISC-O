class ApiResponse():
    def __init__(self, status="fail", message="", raw = ""):
        self.status = status
        self.message = message
        self.raw = raw

    def to_dict(self):
        return {
            "status": self.status,
            "message": self.message,
            "raw": self.raw
        }

