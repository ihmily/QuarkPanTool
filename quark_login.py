import time
from typing import Dict, Union, List
from playwright.sync_api import sync_playwright
from retrying import retry


class QuarkLogin:
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self.headless = headless
        self.slow_mo = slow_mo
        self.context = None

    @staticmethod
    def save_cookies(page) -> None:
        cookie = page.context.cookies()

        with open('cookies.json', 'w', encoding='utf-8') as f:
            f.write(str(cookie))

    @retry
    def login(self) -> None:
        with sync_playwright() as p:
            self.context = p.firefox.launch_persistent_context(
                './gpts_firefox_dir',
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            page = self.context.pages[0]
            page.goto('https://pan.quark.cn/')

            input("请在打开的浏览器中手动登录，登录成功后按 Enter 键继续...")
            self.save_cookies(page)

    @staticmethod
    def cookies_str_to_dict(cookies_str: str) -> Dict[str, str]:
        cookies_dict = {}
        cookies_list = cookies_str.split('; ')
        for cookie in cookies_list:
            key, value = cookie.split('=', 1)
            cookies_dict[key] = value
        return cookies_dict

    @staticmethod
    def transfer_cookies(cookies_list: List[Dict[str, Union[str, int]]]) -> Dict[str, str]:
        cookies_dict = {}
        for cookie in cookies_list:
            if 'quark' in cookie['domain']:
                cookies_dict[cookie['name']] = cookie['value']
        return cookies_dict

    @staticmethod
    def dict_to_cookie_str(cookies_dict: Dict[str, str]) -> str:
        cookie_str = '; '.join([f"{key}={value}" for key, value in cookies_dict.items()])
        return cookie_str

    def check_cookies(self) -> Union[None, Dict[str, str]]:
        try:
            with open('cookies.json', 'r') as f:
                content = f.read()
                if not content:
                    return None
                saved_cookies = eval(content)
            cookies_dict = self.transfer_cookies(saved_cookies)
            timestamp = int(time.time())
            if 'expires' in cookies_dict and timestamp > int(cookies_dict['expires']):
                return None
            return cookies_dict
        except Exception as e:
            print(f"Error checking cookies: {e}")
            return None

    def get_cookies(self) -> Union[str, None]:
        # 从文件加载之前保存的 cookies
        cookies_dict = self.check_cookies()
        if not cookies_dict:
            self.login()
            with open('cookies.json', 'r') as f:
                content = f.read()
                if not content:
                    return
                saved_cookies = eval(content)
            cookies_dict = self.transfer_cookies(saved_cookies)
        return self.dict_to_cookie_str(cookies_dict)


if __name__ == '__main__':
    quark_login = QuarkLogin(headless=False, slow_mo=500)
    quark_login.login()
    cookies = quark_login.get_cookies()
    print(cookies)
