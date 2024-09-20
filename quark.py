# -*- coding: utf-8 -*-

import asyncio
import re
import sys
import httpx
from prettytable import PrettyTable
from tqdm import tqdm
from quark_login import QuarkLogin, CONFIG_DIR
from utils import *
import json
import os
import random
from typing import List, Dict, Union, Tuple, Any


class QuarkPanFileManager:
    def __init__(self, headless: bool = False, slow_mo: int = 0) -> None:
        self.headless: bool = headless
        self.slow_mo: int = slow_mo
        self.folder_id: Union[str, None] = None
        self.user: Union[str, None] = '用户A'
        self.pdir_id: Union[str, None] = '0'
        self.dir_name: Union[str, None] = '根目录'
        self.cookies: str = self.get_cookies()
        self.headers: Dict[str, str] = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/94.0.4606.71 Safari/537.36 Core/1.94.225.400 QQBrowser/12.2.5544.400',
            'origin': 'https://pan.quark.cn',
            'referer': 'https://pan.quark.cn/',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cookie': self.cookies,
        }

    def get_cookies(self) -> str:
        quark_login = QuarkLogin(headless=self.headless, slow_mo=self.slow_mo)
        cookies: str = quark_login.get_cookies()
        return cookies

    @staticmethod
    def get_pwd_id(share_url: str) -> str:
        return share_url.split('?')[0].split('/s/')[1]

    @staticmethod
    def extract_urls(text: str) -> list:
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        return re.findall(url_pattern, text)[0]

    async def get_stoken(self, pwd_id: str) -> str:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            '__dt': random.randint(100, 9999),
            '__t': get_timestamp(13),
        }
        api = f"https://drive-pc.quark.cn/1/clouddrive/share/sharepage/token"
        data = {"pwd_id": pwd_id, "passcode": ""}
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.post(api, json=data, params=params, headers=self.headers, timeout=timeout)
            json_data = response.json()
            if json_data['status'] == 200 and json_data['data']:
                stoken = json_data["data"]["stoken"]
            else:
                stoken = ''
                custom_print(f"文件转存失败，{json_data['message']}")
            return stoken

    async def get_detail(self, pwd_id: str, stoken: str, pdir_fid: str = '0') -> Tuple[
            str, List[Dict[str, Union[int, str]]]]:
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
                    'pdir_fid': pdir_fid,
                    'force': '0',
                    "_page": str(page),
                    '_size': '50',
                    '_sort': 'file_type:asc,updated_at:desc',
                    '__dt': random.randint(200, 9999),
                    '__t': get_timestamp(13),
                }

                timeout = httpx.Timeout(60.0, connect=60.0)
                response = await client.get(api, headers=self.headers, params=params, timeout=timeout)
                json_data = response.json()

                is_owner = json_data['data']['is_owner']
                _total = json_data['metadata']['_total']
                if _total < 1:
                    return is_owner, file_list

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
                        "include_items": file["include_items"] if "include_items" in file else '',
                        "share_fid_token": file["share_fid_token"],
                        "status": file["status"]
                    }
                    file_list.append(d)
                if _total <= _size or _count < _size:
                    return is_owner, file_list

                page += 1

    async def get_sorted_file_list(self, pdir_fid='0', page='1', size='100', fetch_total='false',
                                   sort='') -> Dict[str, Any]:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            'pdir_fid': pdir_fid,
            '_page': page,
            '_size': size,
            '_fetch_total': fetch_total,
            '_fetch_sub_dirs': '1',
            '_sort': sort,
            '__dt': random.randint(100, 9999),
            '__t': get_timestamp(13),
        }

        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.get('https://drive-pc.quark.cn/1/clouddrive/file/sort', params=params,
                                        headers=self.headers, timeout=timeout)
            json_data = response.json()
            return json_data

    async def get_user_info(self) -> str:

        params = {
            'fr': 'pc',
            'platform': 'pc',
        }

        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.get('https://pan.quark.cn/account/info', params=params,
                                        headers=self.headers, timeout=timeout)
            json_data = response.json()
            if json_data['data']:
                nickname = json_data['data']['nickname']
                return nickname
            else:
                input("登录失败！请重新运行本程序，然后在弹出的浏览器中登录夸克账号")
                with open(f'{CONFIG_DIR}/cookies.txt', 'w', encoding='utf-8'):
                    sys.exit(-1)

    async def create_dir(self, pdir_name='新建文件夹') -> None:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            '__dt': random.randint(100, 9999),
            '__t': get_timestamp(13),
        }

        json_data = {
            'pdir_fid': '0',
            'file_name': pdir_name,
            'dir_path': '',
            'dir_init_lock': False,
        }

        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.post('https://drive-pc.quark.cn/1/clouddrive/file', params=params,
                                         json=json_data, headers=self.headers, timeout=timeout)
            json_data = response.json()
            if json_data["code"] == 0:
                custom_print(f'根目录下 {pdir_name} 文件夹创建成功！')
                new_config = {'user': self.user, 'pdir_id': json_data["data"]["fid"], 'dir_name': pdir_name}
                save_config(f'{CONFIG_DIR}/config.json', content=json.dumps(new_config, ensure_ascii=False))
                global to_dir_id
                to_dir_id = json_data["data"]["fid"]
                custom_print(f"自动将保存目录切换至 {pdir_name} 文件夹")
            elif json_data["code"] == 23008:
                custom_print(f'文件夹同名冲突，请更换一个文件夹名称后重试')
            else:
                custom_print(f"错误信息：{json_data['message']}")

    async def run(self, surl: str, folder_id: Union[str, None] = None, download: bool = False) -> None:
        self.folder_id = folder_id
        custom_print(f'文件分享链接：{surl}')
        pwd_id = self.get_pwd_id(surl)
        stoken = await self.get_stoken(pwd_id)
        if not stoken:
            return
        is_owner, data_list = await self.get_detail(pwd_id, stoken)
        files_count = 0
        folders_count = 0
        files_list: List[str] = []
        folders_list: List[str] = []
        files_id_list = []
        file_fid_list = []

        if data_list:
            total_files_count = len(data_list)
            for data in data_list:
                if data['dir']:
                    folders_count += 1
                    folders_list.append(data["file_name"])
                else:
                    files_count += 1
                    files_list.append(data["file_name"])
                    files_id_list.append((data["fid"], data["file_name"]))

            custom_print(f'转存总数：{total_files_count}，文件数：{files_count}，文件夹数：{folders_count} | 支持嵌套')
            custom_print(f'文件转存列表：{files_list}')
            custom_print(f'文件夹转存列表：{folders_list}')

            fid_list = [i["fid"] for i in data_list]
            share_fid_token_list = [i["share_fid_token"] for i in data_list]

            if not self.folder_id:
                custom_print('保存目录ID不合法，请重新获取，如果无法获取，请输入0作为文件夹ID')
                return

            if download:
                if is_owner == 0:
                    custom_print(f'下载文件必须是网盘内文件，请先将文件转存至网盘中')
                    return

                for i in data_list:
                    if i['dir']:
                        data_list2 = [i]
                        not_dir = False
                        while True:
                            data_list3 = []
                            for i2 in data_list2:
                                custom_print(f'开始下载：{i2["file_name"]} 文件夹中的{i2["include_items"]}个文件')
                                is_owner, file_data_list = await self.get_detail(pwd_id, stoken, pdir_fid=i2['fid'])
                                folder = i["file_name"]
                                fid_list = [i["fid"] for i in file_data_list]
                                await self.quark_file_download(fid_list, folder=folder)
                                file_fid_list.extend([i for i in file_data_list if not i2['dir']])
                                dir_list = [i for i in file_data_list if i['dir']]
                                if not dir_list:
                                    not_dir = True
                                data_list3.extend(dir_list)
                            data_list2 = data_list3
                            if not data_list2 or not_dir:
                                break

                if len(files_id_list) > 0 or len(file_fid_list) > 0:
                    fid_list = [i[0] for i in files_id_list]
                    file_fid_list.extend(fid_list)
                    await self.quark_file_download(file_fid_list, folder='.')

            else:
                if is_owner == 1:
                    custom_print(f'网盘中已经存在该文件，无需再次转存')
                    return
                task_id = await self.get_share_save_task_id(pwd_id, stoken, fid_list, share_fid_token_list,
                                                            to_pdir_fid=self.folder_id)
                await self.submit_task(task_id)
            print()

    async def get_share_save_task_id(self, pwd_id: str, stoken: str, first_ids: List[str], share_fid_tokens: List[str],
                                     to_pdir_fid: str = '0') -> str:
        task_url = "https://drive.quark.cn/1/clouddrive/share/sharepage/save"
        params = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "__dt": random.randint(600, 9999),
            "__t": get_timestamp(13),
        }
        data = {"fid_list": first_ids,
                "fid_token_list": share_fid_tokens,
                "to_pdir_fid": to_pdir_fid, "pwd_id": pwd_id,
                "stoken": stoken, "pdir_fid": "0", "scene": "link"}

        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.post(task_url, json=data, headers=self.headers, params=params, timeout=timeout)
            json_data = response.json()
            task_id = json_data['data']['task_id']
            custom_print(f'获取任务ID：{task_id}')
            return task_id

    @staticmethod
    async def download_file(download_url: str, save_path: str, headers: dict) -> None:
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            async with client.stream("GET", download_url, headers=headers, timeout=timeout) as response:
                total_size = int(response.headers["content-length"])
                with open(save_path, "wb") as f:
                    with tqdm(total=total_size, unit="B", unit_scale=True,
                              desc=os.path.basename(save_path),
                              ncols=80) as pbar:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            pbar.update(len(chunk))

    async def quark_file_download(self, fids: List[str], folder: str = '') -> None:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            '__dt': random.randint(600, 9999),
            '__t': get_timestamp(13),
        }

        data = {
            'fids': fids
        }
        download_api = 'https://drive-pc.quark.cn/1/clouddrive/file/download'
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.post(download_api, json=data, headers=self.headers, params=params, timeout=timeout)
            json_data = response.json()
            data_list = json_data.get('data', None)
            if json_data['status'] != 200:
                custom_print(f"文件下载地址列表获取失败, {json_data['message']}")
                return
            elif data_list:
                custom_print('文件下载地址列表获取成功')

            save_folder = f'downloads/{folder}' if folder else 'downloads'
            os.makedirs(save_folder, exist_ok=True)
            n = 0
            for i in data_list:
                n += 1
                filename = i["file_name"]
                custom_print(f'开始下载第{n}个文件-{filename}')
                download_url = i["download_url"]
                save_path = os.path.join(save_folder, filename)
                await self.download_file(download_url, save_path, headers=self.headers)

    async def submit_task(self, task_id: str, retry: int = 50) -> Union[
            bool, Dict[str, Union[str, Dict[str, Union[int, str]]]]]:

        for i in range(retry):
            # 随机暂停100-50毫秒
            await asyncio.sleep(random.randint(500, 1000) / 1000)
            custom_print(f'第{i + 1}次提交任务')
            submit_url = (f"https://drive-pc.quark.cn/1/clouddrive/task?pr=ucpro&fr=pc&uc_param_str=&task_id={task_id}"
                          f"&retry_index={i}&__dt=21192&__t={get_timestamp(13)}")

            async with httpx.AsyncClient() as client:
                timeout = httpx.Timeout(60.0, connect=60.0)
                response = await client.get(submit_url, headers=self.headers, timeout=timeout)
                json_data = response.json()

            if json_data['message'] == 'ok':
                if json_data['data']['status'] == 2:
                    if 'to_pdir_name' in json_data['data']['save_as']:
                        folder_name = json_data['data']['save_as']['to_pdir_name']
                    else:
                        folder_name = ' 根目录'
                    if json_data['data']['task_title'] == '分享-转存':
                        custom_print(f"结束任务ID：{task_id}")
                        custom_print(f'文件保存位置：{folder_name} 文件夹')
                    return json_data
            else:
                if json_data['code'] == 32003 and 'capacity limit' in json_data['message']:
                    input(f"[{get_datetime()}] 转存失败，网盘容量不足！请注意当前已成功保存的个数，避免重复保存")
                elif json_data['code'] == 41013:
                    input(f"[{get_datetime()}] ”{to_dir_name}“ 网盘文件夹不存在，请重新运行按3切换保存目录后重试！")
                else:
                    input(f"[{get_datetime()}] 错误信息：{json_data['message']}")
                sys.exit(f'[{get_datetime()}] 已退出程序')

    def init_config(self, _user, _pdir_id, _dir_name):
        try:
            os.makedirs('share', exist_ok=True)
            json_data = read_config(f'{CONFIG_DIR}/config.json', 'json')
            if json_data:
                user = json_data.get('user', 'jack')
                if user != _user:
                    _pdir_id = '0'
                    _dir_name = '根目录'
                    new_config = {'user': _user, 'pdir_id': _pdir_id, 'dir_name': _dir_name}
                    save_config(f'{CONFIG_DIR}/config.json', content=json.dumps(new_config, ensure_ascii=False))
                else:
                    _pdir_id = json_data.get('pdir_id', '0')
                    _dir_name = json_data.get('dir_name', '根目录')
        except json.decoder.JSONDecodeError:
            new_config = {'user': self.user, 'pdir_id': self.pdir_id, 'dir_name': self.dir_name}
            save_config(f'{CONFIG_DIR}/config.json', content=json.dumps(new_config, ensure_ascii=False))
        return _user, _pdir_id, _dir_name

    async def load_folder_id(self, renew=False) -> Union[tuple, None]:

        self.user = await self.get_user_info()
        self.user, self.pdir_id, self.dir_name = self.init_config(self.user, self.pdir_id, self.dir_name)
        if not renew:
            custom_print(f'用户名：{self.user}')
            custom_print(f'你当前选择的网盘保存目录: {self.dir_name} 文件夹')

        if renew:
            pdir_id = input(f'[{get_datetime()}] 请输入保存位置的文件夹ID(可为空): ')
            if pdir_id == '0':
                self.dir_name = '根目录'
                new_config = {'user': self.user, 'pdir_id': self.pdir_id, 'dir_name': self.dir_name}
                save_config(f'{CONFIG_DIR}/config.json', content=json.dumps(new_config, ensure_ascii=False))

            elif len(pdir_id) < 32:
                file_list_data = await self.get_sorted_file_list()
                fd_list = file_list_data['data']['list']
                fd_list = [{i['fid']: i['file_name']} for i in fd_list if i.get('dir')]
                if fd_list:
                    table = PrettyTable(['序号', '文件夹ID', '文件夹名称'])
                    for idx, item in enumerate(fd_list, 1):
                        key, value = next(iter(item.items()))
                        table.add_row([idx, key, value])
                    print(table)
                    num = input(f'[{get_datetime()}] 请选择你要保存的位置（输入对应序号）: ')
                    while not num:
                        print('请输入文件夹对应序号')
                    item = fd_list[int(num) - 1]
                    self.pdir_id, self.dir_name = next(iter(item.items()))
                    new_config = {'user': self.user, 'pdir_id': self.pdir_id, 'dir_name': self.dir_name}
                    save_config(f'{CONFIG_DIR}/config.json', content=json.dumps(new_config, ensure_ascii=False))

        return self.pdir_id, self.dir_name

    async def get_share_task_id(self, fid: str, file_name: str, url_type: int = 1, expired_type: int = 2,
                                password: str = '') -> str:

        json_data = {
            "fid_list": [
                fid
            ],
            "title": file_name,

            "url_type": url_type,
            "expired_type": expired_type
        }
        if url_type == 2:
            if password:
                json_data["passcode"] = password
            else:
                json_data["passcode"] = generate_random_code()

        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
        }

        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.post('https://drive-pc.quark.cn/1/clouddrive/share', params=params,
                                         json=json_data, headers=self.headers, timeout=timeout)
            json_data = response.json()
            return json_data['data']['task_id']

    async def get_share_id(self, task_id: str) -> str:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
            'task_id': task_id,
            'retry_index': '0',
        }
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.get('https://drive-pc.quark.cn/1/clouddrive/task', params=params,
                                        headers=self.headers, timeout=timeout)
            json_data = response.json()
            return json_data['data']['share_id']

    async def submit_share(self, share_id: str) -> None:
        params = {
            'pr': 'ucpro',
            'fr': 'pc',
            'uc_param_str': '',
        }

        json_data = {
            'share_id': share_id,
        }
        async with httpx.AsyncClient() as client:
            timeout = httpx.Timeout(60.0, connect=60.0)
            response = await client.post('https://drive-pc.quark.cn/1/clouddrive/share/password', params=params,
                                         json=json_data, headers=self.headers, timeout=timeout)
            json_data = response.json()
            share_url = json_data['data']['share_url']
            if 'passcode' in json_data['data']:
                share_url = share_url + f"?pwd={json_data['data']['passcode']}"
            return share_url

    async def share_run(self, share_url: str, folder_id: Union[str, None] = None, url_type: int = 1,
                        expired_type: int = 2, password: str = '') -> None:
        first_dir = ''
        second_dir = ''
        try:
            self.folder_id = folder_id
            custom_print(f'文件夹网页地址：{share_url}')
            pwd_id = share_url.rsplit('/', maxsplit=1)[1].split('-')[0]

            first_page = 1
            n = 0
            error = 0
            os.makedirs('share', exist_ok=True)
            save_share_path = 'share/share_url.txt'

            safe_copy(save_share_path, 'share/share_url_backup.txt')
            with open(save_share_path, 'w', encoding='utf-8'):
                pass
            while True:
                json_data = await self.get_sorted_file_list(pwd_id, page=str(first_page), size='50', fetch_total='1',
                                                            sort='file_type:asc,file_name:asc')
                for i1 in json_data['data']['list']:
                    if i1['dir']:
                        first_dir = i1['file_name']
                        second_page = 1
                        while True:
                            # print(f'正在获取{first_dir}第{first_page}页，二级目录第{second_page}页，目前共分享{n}文件')
                            json_data2 = await self.get_sorted_file_list(i1['fid'], page=str(second_page),
                                                                         size='50', fetch_total='1',
                                                                         sort='file_type:asc,file_name:asc')
                            for i2 in json_data2['data']['list']:
                                if i2['dir']:
                                    n += 1
                                    share_success = False
                                    share_error_msg = ''
                                    fid = ''
                                    for i in range(3):
                                        try:
                                            second_dir = i2['file_name']
                                            custom_print(f'{n}.开始分享 {first_dir}/{second_dir} 文件夹')
                                            random_time = random.choice([0.5, 1, 1.5, 2])
                                            await asyncio.sleep(random_time)
                                            # print('获取到文件夹ID：', i2['fid'])
                                            fid = i2['fid']
                                            task_id = await self.get_share_task_id(fid, second_dir, url_type=url_type,
                                                                                   expired_type=expired_type,
                                                                                   password=password)
                                            share_id = await self.get_share_id(task_id)
                                            share_url = await self.submit_share(share_id)
                                            with open(save_share_path, 'a', encoding='utf-8') as f:
                                                content = f'{n} | {first_dir} | {second_dir} | {share_url}'
                                                f.write(content + '\n')
                                                custom_print(f'{n}.分享成功 {first_dir}/{second_dir} 文件夹')
                                                share_success = True
                                                break

                                        except Exception as e:
                                            share_error_msg = e
                                            error += 1

                                    if not share_success:
                                        print('分享失败：', share_error_msg)
                                        save_config('./share/share_error.txt',
                                                    content=f'{error}.{first_dir}/{second_dir} 文件夹\n', mode='a')
                                        save_config('./share/retry.txt',
                                                    content=f'{n} | {first_dir} | {second_dir} | {fid}\n', mode='a')
                            second_total = json_data2['metadata']['_total']
                            second_size = json_data2['metadata']['_size']
                            second_page = json_data2['metadata']['_page']
                            if second_size * second_page >= second_total:
                                break
                            second_page += 1

                second_total = json_data['metadata']['_total']
                second_size = json_data['metadata']['_size']
                second_page = json_data['metadata']['_page']
                if second_size * second_page >= second_total:
                    break
                first_page += 1
            custom_print(f"总共分享了 {n} 个文件夹，已经保存至 {save_share_path}")

        except Exception as e:
            print('分享失败：', e)
            with open('./share/share_error.txt', 'a', encoding='utf-8') as f:
                f.write(f'{first_dir}/{second_dir} 文件夹')

    async def share_run_retry(self, retry_url: str, url_type: int = 1, expired_type: int = 2, password: str = ''):

        data_list = retry_url.split('\n')
        n = 0
        error = 0
        save_share_path = 'share/retry_share_url.txt'
        error_data = []
        for i1 in data_list:
            data = i1.split(' | ')
            if data and len(data) == 4:
                first_dir = data[-3]
                second_dir = data[-2]
                fid = data[-1]
                share_error_msg = ''
                for i in range(3):
                    try:
                        task_id = await self.get_share_task_id(fid, second_dir, url_type=url_type,
                                                               expired_type=expired_type,
                                                               password=password)
                        # print('获取到任务ID：', task_id)
                        share_id = await self.get_share_id(task_id)
                        # print('获取到分享ID：', share_id)
                        share_url = await self.submit_share(share_id)
                        with open(save_share_path, 'a', encoding='utf-8') as f:
                            content = f'{n} | {first_dir} | {second_dir} | {share_url}'
                            f.write(content + '\n')
                            custom_print(f'{n}.分享成功 {first_dir}/{second_dir} 文件夹')
                            share_success = True
                            break
                    except Exception as e:
                        # print('分享失败：', e)
                        share_error_msg = e
                        error += 1

                if not share_success:
                    print('分享失败：', share_error_msg)
                    error_data.append(i1)
        error_content = '\n'.join(error_data)
        save_config(path='./share/retry.txt', content=error_content, mode='w')


def load_url_file(fpath: str) -> List[str]:
    with open(fpath, 'r') as f:
        content = f.readlines()

    url_list = [line.strip() for line in content if 'http' in line]
    return url_list


def print_ascii():
    print(r"""║                                     _                                  _                     _       ║    
║       __ _   _   _    __ _   _ __  | | __    _ __     __ _   _ __     | |_    ___     ___   | |      ║
║      / _  | | | | |  / _  | | '__| | |/ /   | '_ \   / _  | |  _ \    | __|  / _ \   / _ \  | |      ║
║     | (_| | | |_| | | (_| | | |    |   <    | |_) | | (_| | | | | |   | |_  | (_) | | (_) | | |      ║
║      \__, |  \__,_|  \__,_| |_|    |_|\_\   | .__/   \__,_| |_| |_|    \__|  \___/   \___/  |_|      ║
║         |_|                                 |_|                                                      ║""")


def print_menu() -> None:
    print("╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗")
    print_ascii()
    print("║                                                                                                      ║")
    print("║                                  Author: Hmily  Version: 0.0.3                                       ║")
    print("║                          GitHub: https://github.com/ihmily/QuarkPanTool                              ║")
    print("╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣")
    print(r"║     1.分享地址转存文件   2.批量生成分享链接   3.切换网盘保存目录   4.创建网盘文件夹   5.下载到本地   q.退出        ║")
    print("╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝")


if __name__ == '__main__':
    quark_file_manager = QuarkPanFileManager(headless=False, slow_mo=500)
    while True:
        print_menu()

        to_dir_id, to_dir_name = asyncio.run(quark_file_manager.load_folder_id())

        input_text = input("请输入你的选择(1—5或q)：")

        if input_text and input_text.strip() in ['q', 'Q']:
            print("已退出程序！")
            sys.exit(0)

        if input_text and input_text.strip() in [str(i) for i in range(1, 6)]:
            if input_text.strip() == '1':
                save_option = input("是否批量转存(1是 2否)：")
                if save_option and save_option == '1':
                    try:
                        urls = load_url_file('./url.txt')
                        if not urls:
                            custom_print('\n分享地址为空！请先在url.txt文件中输入分享地址(一行一个)')
                            continue

                        custom_print(f"\r检测到url.txt文件中有{len(urls)}条分享链接")
                        ok = input("请你确认是否开始批量保存(确认请按2):")
                        if ok and ok.strip() == '2':
                            for index, url in enumerate(urls):
                                print(f"正在转存第{index + 1}个")
                                asyncio.run(quark_file_manager.run(url.strip(), to_dir_id))
                    except FileNotFoundError:
                        with open('url.txt', 'w', encoding='utf-8'):
                            sys.exit(-1)
                else:
                    url = input("请输入夸克文件分享地址：")
                    if url and len(url.strip()) > 20:
                        asyncio.run(quark_file_manager.run(url.strip(), to_dir_id))

            elif input_text.strip() == '2':
                share_option = input("请输入你的选择(1分享 2重试分享)：")
                if share_option and share_option == '1':
                    url = input("请输入需要分享的文件夹网页端页面地址：")
                    if not url or len(url.strip()) < 20:
                        continue
                else:
                    try:
                        url = read_config(path='./share/retry.txt', mode='r')
                        if not url:
                            print('\nretry.txt 为空！请检查文件')
                            continue
                    except FileNotFoundError:
                        save_config('./share/retry.txt', content='')
                        print('\nshare/retry.txt 文件为空！')
                        continue

                expired_option = {"1": 2, "2": 3, "3": 4, "4": 1}
                print("1.1天  2.7天  3.30天  4.永久")
                select_option = input("请输入分享时长选项：")
                _expired_type = expired_option[select_option] if select_option in expired_option else 4
                is_private = input("是否加密(1否/2是)：")
                url_encrypt = 2 if is_private == '2' else 1
                passcode = input('请输入你想设置的分享提取码(直接回车，可随机生成):') if url_encrypt == 2 else ''
                if share_option and share_option == '1':
                    asyncio.run(quark_file_manager.share_run(
                        url.strip(), folder_id=to_dir_id, url_type=int(url_encrypt),
                        expired_type=int(_expired_type), password=passcode))
                else:
                    asyncio.run(quark_file_manager.share_run_retry(url.strip(), url_type=url_encrypt,
                                                                   expired_type=_expired_type, password=passcode))

            elif input_text.strip() == '3':
                to_dir_id, to_dir_name = asyncio.run(quark_file_manager.load_folder_id(renew=True))
                custom_print(f"已切换保存目录至网盘 {to_dir_name} 文件夹\n")

            elif input_text.strip() == '4':
                create_name = input("请输入需要创建的文件夹名称：")
                if create_name:
                    asyncio.run(quark_file_manager.create_dir(create_name.strip()))
                else:
                    custom_print("创建的文件夹名称不可为空！")

            elif input_text.strip() == '5':
                try:
                    is_batch = input("输入你的选择(1单个地址下载，2批量下载):")
                    if is_batch:
                        if is_batch.strip() == '1':
                            url = input("请输入夸克文件分享地址：")
                            asyncio.run(quark_file_manager.run(url.strip(), to_dir_id, download=True))
                        elif is_batch.strip() == '2':
                            urls = load_url_file('./url.txt')
                            if not urls:
                                print('\n分享地址为空！请先在url.txt文件中输入分享地址(一行一个)')
                                continue

                            for index, url in enumerate(urls):
                                asyncio.run(quark_file_manager.run(url.strip(), to_dir_id, download=True))

                except FileNotFoundError:
                    with open('url.txt', 'w', encoding='utf-8'):
                        sys.exit(-1)

        else:
            custom_print("输入无效，请重新输入")
