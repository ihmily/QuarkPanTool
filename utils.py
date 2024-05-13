import time
from datetime import datetime
from typing import Union


def get_datetime(timestamp: Union[int, float, None] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if timestamp is None or not isinstance(timestamp, (int, float)):
        return datetime.today().strftime(fmt)
    else:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.strftime(fmt)
        return formatted_time


def custom_print(message) -> None:
    print(f'[{get_datetime()}] {message}')


def get_timestamp(length: int) -> int:
    if length == 13:
        return int(time.time()) * 1000
    else:
        return int(time.time())
