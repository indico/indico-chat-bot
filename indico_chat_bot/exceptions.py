class InvalidTimeDeltaFormat(Exception):
    def __init__(self, time_delta):
        message = f"Wrong format for timedelta: {time_delta}"
        super().__init__(message)


class InvalidTime(Exception):
    def __init__(self):
        message = "Invalid time!"
        super().__init__(message)


class UnknownNotifier(SystemError):
    def __init__(self, channel_type):
        message = f"Unknown notifier '{channel_type}'"
        super().__init__(message)
