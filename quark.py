import asyncio
import random
import time
from datetime import datetime
from typing import List, Dict, Union

import httpx
from prettytable import PrettyTable


class QuarkPanFileManager:
    def __init__(self, _headless: bool = False, _slow_mo: int = 0) -> None:
        self.headers: Dict[str, str] = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/94.0.4606.71 Safari/537.36 Core/1.94.225.400 QQBrowser/12.2.5544.400',
            'origin': 'https://pan.quark.cn',
            'referer': 'https://pan.quark.cn/',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': self.get_cookies(),
        }
        self.folder_id: Union[str, None] = None

    @staticmethod
    def get_cookies() -> str:
        from quark_login import QuarkLogin
        quark_login = QuarkLogin(headless=False, slow_mo=500)
        cookies: str = quark_login.get_cookies()
        return cookies

    @staticmethod
    def get_pwd_id(share_url: str) -> str:
        return share_url.split('?')[0].split('/s/')[1]

    @staticmethod
    def generate_timestamp(length: int) -> int:
        if length == 13:
            return int(time.time()) * 1000
        else:
            return int(time.time())

    async def get_stoken(self, pwd_id: str) -> str:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            '__dt': random.randint(100, 9999),
            '__t': self.generate_timestamp(13),
        }
        api = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token"
        data = {"pwd_id": pwd_id, "passcode": ""}
        async with httpx.AsyncClient() as client:
            response = await client.post(api, json=data, params=params, headers=self.headers)
            json_data = response.json()
            return json_data["data"]["stoken"] if json_data.get('data') else ""

    async def get_detail(self, pwd_id: str, stoken: str) -> List[Dict[str, Union[int, str]]]:
        api = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/detail"
        page = 1
        file_list: List[Dict[str, Union[int, str]]] = []

        async with httpx.AsyncClient() as client:
            while True:
                params = {
                    'pr': 'ucpro',
                    'fr': 'pc',
                    'uc_param_str': '',
                    "pwd_id": pwd_id,
                    "stoken": stoken,
                    "pdir_fid": 0,
                    "force": 0,
                    "_page": page,
                    "_size": "50",
                    '_sort': 'file_type:asc,updated_at:desc',
                    '__dt': random.randint(600, 9999),
                    '__t': self.generate_timestamp(13),
                }
                response = await client.get(api, headers=self.headers, params=params)
                json_data = response.json()

                _total = json_data['metadata']['_total']
                if _total < 1:
                    return file_list

                _size = json_data['metadata']['_size']  # 每页限制数量
                _count = json_data['metadata']['_count']  # 当前页数量

                _list = json_data["data"]["list"]
                for file in _list:
                    d: Dict[str, Union[int, str]] = {
                        "fid": file["fid"],
                        "file_name": file["file_name"],
                        "file_type": file["file_type"],
                        "dir": file["dir"],
                        "pdir_fid": file["pdir_fid"],
                        "include_items": file["include_items"],
                        "share_fid_token": file["share_fid_token"],
                        "status": file["status"]
                    }
                    file_list.append(d)

                if _total <= _size or _count < _size:
                    return file_list

                page += 1

    async def get_sorted_file_list(self, pdir_fid=0) -> List[Dict[str, str]]:
        """获取文件夹下的文件列表"""
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            'pdir_fid': pdir_fid,
            '_page': '1',
            '_size': '100',
            '_fetch_total': 'false',
            '_fetch_sub_dirs': '1',
            '_sort': '',
            '__dt': random.randint(100, 9999),
            '__t': self.generate_timestamp(13),
        }

        async with httpx.AsyncClient() as client:
            response = await client.get('https://drive-pc.quark.cn/1/clouddrive/file/sort', params=params,
                                        headers=self.headers)
            json_data = response.json()
            _list = json_data['data']['list']
            folder_list = []
            for i in _list:
                if i['dir']:
                    folder_list.append({i['fid']: i['file_name']})
            return folder_list

    async def run(self, surl: str, folder_id: Union[str, None] = None) -> None:
        self.folder_id = folder_id
        print(f'[{self.get_datetime()}] 文件分享链接：{surl}')
        pwd_id = self.get_pwd_id(surl)
        stoken = await self.get_stoken(pwd_id)
        data_list = await self.get_detail(pwd_id, stoken)

        files_count = 0
        folders_count = 0
        files_list: List[str] = []
        folders_list: List[str] = []

        if data_list:
            total_files_count = len(data_list)
            for data in data_list:
                if data['dir']:
                    folders_count += 1
                    folders_list.append(data["file_name"])
                else:
                    files_count += 1
                    files_list.append(data["file_name"])
            print(f'[{self.get_datetime()}] 转存总数：{total_files_count}，文件数：{files_count}，文件夹数：{folders_count}')
            print(f'[{self.get_datetime()}] 文件转存列表：{files_list}')
            print(f'[{self.get_datetime()}] 文件夹转存列表：{folders_list}')

            fid_list = [i["fid"] for i in data_list]
            share_fid_token_list = [i["share_fid_token"] for i in data_list]

            if not self.folder_id:
                print('保存目录ID不合法，请重新获取，如果无法获取，请输入0作为文件夹ID')
                return

            task_id = await self.get_task_id(pwd_id, stoken, fid_list, share_fid_token_list, to_pdir_fid=self.folder_id)
            await self.submit_task(task_id)
            print()

    async def get_task_id(self, pwd_id: str, stoken: str, first_ids: List[str], share_fid_tokens: List[str],
                          to_pdir_fid: str = '0') -> str:
        task_url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": random.randint(600, 9999),
            "__t": self.generate_timestamp(13),
        }
        data = {"fid_list": first_ids,
                "fid_token_list": share_fid_tokens,
                "to_pdir_fid": to_pdir_fid, "pwd_id": pwd_id,
                "stoken": stoken, "pdir_fid": "0", "scene": "link"}

        async with httpx.AsyncClient() as client:
            response = await client.post(task_url, json=data, headers=self.headers, params=params)
            json_data = response.json()
            task_id = json_data['data']['task_id']
            print(f'[{self.get_datetime()}] 获取任务ID：{task_id}')
            return task_id

    @staticmethod
    def save_pid(pid, name):
        with open('config.txt', 'w', encoding='utf-8') as f:
            f.write(f"{pid},{name}")

    @staticmethod
    def get_datetime(timestamp: Union[int, float, None] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        if timestamp is None or not isinstance(timestamp, (int, float)):
            return datetime.today().strftime(fmt)
        else:
            dt = datetime.fromtimestamp(timestamp)
            formatted_time = dt.strftime(fmt)
            return formatted_time

    async def submit_task(self, task_id: str, retry: int = 50) -> Union[
            bool, Dict[str, Union[str, Dict[str, Union[int, str]]]]]:
        """根据task_id进行任务"""
        for i in range(retry):
            print(f'[{self.get_datetime()}] 第{i + 1}次提交任务')
            submit_url = (f"https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&uc_param_str=&task_id={task_id}"
                          f"&retry_index={i}&__dt=21192&__t={self.generate_timestamp(13)}")

            async with httpx.AsyncClient() as client:
                response = await client.get(submit_url, headers=self.headers)
                json_data = response.json()

            if json_data['message'] == 'ok':
                if json_data['data']['status'] == 2:
                    if 'to_pdir_name' in json_data['data']['save_as']:
                        folder_name = json_data['data']['save_as']['to_pdir_name']
                    else:
                        folder_name = ' 根目录'
                    if json_data['data']['task_title'] == '分享-转存':
                        print(f"[{self.get_datetime()}] 结束任务ID：{task_id}")
                        print(f'[{self.get_datetime()}] 文件转存目录：“{folder_name}” 文件夹')
                    return json_data
            else:
                print('任务执行失败！')

    async def load_folder_id(self, renew=False):
        try:

            with open('config.txt', 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    pdir_config = content.strip().replace('，', ',').split(',')
                else:
                    pdir_config = None
        except FileNotFoundError:
            with open('config.txt', 'w', encoding='utf-8'):
                pdir_config = None

        if not renew and pdir_config and len(pdir_config) > 1:
            pdir_id, dir_name = pdir_config
            self.save_pid(pdir_id, dir_name)
        else:
            dir_name = ''
            pdir_id = input(f'[{self.get_datetime()}] 请输入保存位置的文件夹ID(可为空): ')
            if pdir_id == '0':
                dir_name = '根目录'
                self.save_pid(pdir_id, dir_name)

            elif len(pdir_id) < 32:
                fd_list = await self.get_sorted_file_list()
                if fd_list:
                    table = PrettyTable(['序号', '文件夹ID', '文件夹名称'])
                    for idx, item in enumerate(fd_list, 1):
                        key, value = next(iter(item.items()))
                        table.add_row([idx, key, value])
                    print(table)
                    num = input(f'[{self.get_datetime()}] 请选择你要保存的位置（输入对应序号）: ')
                    item = fd_list[int(num) - 1]
                    pdir_id, dir_name = next(iter(item.items()))
                    self.save_pid(pdir_id, dir_name)
        if not renew:
            print(f'[{self.get_datetime()}] 你当前选择的网盘保存目录: ”{dir_name}“ 文件夹')
        return pdir_id, dir_name


def load_url_file(fpath: str) -> list:
    with open(fpath, 'r') as f:
        content = f.readlines()

    url_list = [line.strip() for line in content if 'http' in line]
    return url_list


if __name__ == '__main__':
    quark_file_manager = QuarkPanFileManager()
    while True:
        print("---------------------------------------------------------------")
        print("|   1.单个分享地址转存   2.批量分享地址转存   3.切换保存目录   q.退出  |")
        print("---------------------------------------------------------------")

        to_dir_id, to_dir_name = asyncio.run(quark_file_manager.load_folder_id())

        input_text = input("请输入你的选择(1—3或q)：")

        if input_text and input_text.strip() in ['q', 'Q']:
            print("退出程序！")
            break

        if input_text and input_text.strip() in ['1', '2', '3']:
            if input_text.strip() == '1':
                url = input("请输入夸克文件分享地址：")
                if url and url.strip():
                    asyncio.run(quark_file_manager.run(url.strip(), to_dir_id))

            elif input_text.strip() == '2':
                try:
                    urls = load_url_file('./url.txt')
                    if not urls:
                        print('\n分享地址为空！请先在url.txt文件中输入分享地址(每行一个)')
                        continue
                    ok = input("请你是否开始确认批量保存(确认请按2):")
                    if ok == '1':
                        for index, url in enumerate(urls):
                            print(f"第{index + 1}条分享链接")
                            asyncio.run(quark_file_manager.run(url.strip(), to_dir_id))
                except FileNotFoundError:
                    with open('url.txt', 'w', encoding='utf-8'):
                        break

            elif input_text.strip() == '3':
                to_dir_id, to_dir_name = asyncio.run(quark_file_manager.load_folder_id(renew=True))
                print(f"切换保存目录至网盘 ”{to_dir_name}“ 文件夹\n")

        else:
            print("输入无效，请重新输入")
