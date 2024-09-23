import json
import os
import random
import shutil
import string
import time
from datetime import datetime
from typing import Union
from colorama import Fore, Style


def get_datetime(timestamp: Union[int, float, None] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if timestamp is None or not isinstance(timestamp, (int, float)):
        return datetime.today().strftime(fmt)
    else:
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.strftime(fmt)
        return formatted_time


def custom_print(message, error_msg=False) -> None:
    if error_msg:
        print(Fore.RED + f'[{get_datetime()}] {message}' + Style.RESET_ALL)
    else:
        print(f'[{get_datetime()}] {message}')


def get_timestamp(length: int) -> int:
    if length == 13:
        return int(time.time()) * 1000
    else:
        return int(time.time())


def save_config(path: str, content: str, mode: str = 'w'):
    with open(path, mode, encoding='utf-8') as f:
        f.write(content)


def read_config(path: str, read_type: str = None, mode: str = 'r') -> Union[dict, str]:
    with open(path, mode, encoding='utf-8') as config_file:
        if read_type != 'json':
            return config_file.read()
        else:
            return json.load(config_file)


def safe_copy(src, dst):
    if not os.path.exists(src):
        print(f"源文件不存在，跳过复制：{src}")
        return

    if os.path.exists(dst):
        os.remove(dst)
        print(f"目标文件已存在，已删除：{dst}")

    try:
        shutil.copy(src, dst)
        print(f"文件已复制到：{dst}")
    except Exception as e:
        print('备份share_url.txt文件错误，', e)


def generate_random_code(length=4):
    characters = string.ascii_letters + string.digits
    random_code = ''.join(random.choice(characters) for _ in range(length))
    return random_code
