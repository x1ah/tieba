import logging
import requests
import hashlib
import time

from typing import List


logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(asctime)s: %(message)s"
)


class MsgChannel:
    name: str = "unknown channel"

    def send(self, text: str):
        raise NotImplemented("not implemented")


class LarkChannel(MsgChannel):
    name = "飞书自定义机器人"

    def __init__(self, webhook: str) -> None:
        self.webhook = webhook

    def send(self, text: str):
        return requests.post(
            self.webhook, json={"msg_type": "text", "content": {"text": text}}
        )


class WorkWechatBotChannel(MsgChannel):
    name = "企业微信机器人"

    def __init__(self, key: str) -> None:
        self.webhook = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"

    def send(self, text: str):
        return requests.post(
            self.webhook, json={"msgtype": "text", "text": {"content": text}}
        )


class Tieba:
    bduss: str
    logger: logging.Logger
    channel: MsgChannel

    def __init__(self, bduss: str, channels: List[MsgChannel] = None) -> None:
        """bduss: 贴吧 cookie"""
        self.bduss = bduss
        self.logger = logging.getLogger(__name__)
        self.channels = channels or []

    @property
    def session(self) -> requests.Session:
        if not getattr(self, "_session", None):
            self._session = requests.Session()

        return self._session

    @property
    def tbs(self) -> str:
        if getattr(self, "_tbs", None):
            return self._tbs

        resp = self.session.get(
            url="http://tieba.baidu.com/dc/common/tbs",
            headers={
                "Cookie": f"BDUSS={self.bduss}",
                "Host": "tieba.baidu.com",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
                "Referer": "https://tieba.baidu.com/",
            },
        )
        if resp.status_code != 200:
            self.logger.error("get_tbs error: %s", resp.text)
            return ""

        self._tbs = resp.json()["tbs"]
        return self._tbs

    @classmethod
    def signature(cls, data) -> str:
        val = "".join(f"{k}={data[k]}" for k in sorted(data))
        return hashlib.md5((val + "tiebaclient!!!").encode()).hexdigest().upper()

    def get_likes(self, page_no: int, retry_times: int = 0):
        data = {
            "BDUSS": self.bduss,
            "_client_type": "2",
            "_client_id": "wappc_1534235498291_488",
            "_client_version": "9.7.8.0",
            "_phone_imei": "000000000000000",
            "from": "1008621y",
            "page_no": str(page_no),
            "page_size": "200",
            "model": "MI+5",
            "net_type": "1",
            "timestamp": str(int(time.time())),
            "vcode_tag": "11",
        }
        sign = self.signature(data)
        data["sign"] = sign
        resp = self.session.post(
            "http://c.tieba.baidu.com/c/f/forum/like",
            data=data,
        )
        if resp.status_code != 200:
            self.logger.error("获取关注的贴吧错误: ", resp.text)
            if retry_times < 3:
                return self.get_likes(page_no, retry_times + 1)
            return []
        resp_json = resp.json()
        has_next = resp_json.get("has_more") == "1"
        forum_list = []
        forum_list += resp_json.get("forum_list", {}).get("non-gconforum", [])
        forum_list += resp_json.get("forum_list", {}).get("gconforum", [])
        if has_next:
            forum_list += self.get_likes(page_no + 1)
        return forum_list

    def sign(self, fid: str, name: str) -> bool:
        """签到"""
        data = {
            "_client_type": "2",
            "_client_id": "wappc_1534235498291_488",
            "_client_version": "9.7.8.0",
            "_phone_imei": "000000000000000",
            "model": "MI+5",
            "net_type": "1",
            "timestamp": str(int(time.time())),
            "vcode_tag": "11",
            "BDUSS": self.bduss,
            "fid": fid,
            "kw": name,
            "tbs": self.tbs,
        }
        sig = self.signature(data)
        data["sign"] = sig
        resp = self.session.post("http://c.tieba.baidu.com/c/c/forum/sign", data=data)
        if resp.status_code != 200:
            self.logger.error(f"[{name}] 签到失败: {resp.text}")
            return False

        error_code = int(resp.json().get("error_code") or 0)
        error_msg = resp.json().get("error_msg", "")
        if error_code != 0:
            self.logger.error(f"[{name}] 签到失败: {error_msg}")
            return False

        self.logger.info(f"[{name}] 签到成功")
        return True

    def run(self):
        forums = self.get_likes(1)
        n_succeed, n_faild = 0, 0
        for forum in forums:
            try:
                succeed = self.sign(forum["id"], forum["name"])
                if succeed:
                    n_succeed += 1
                else:
                    n_faild += 1
            except Exception as e:
                self.logger.error(f"签到失败: {str(e)}")
            time.sleep(1.3)

        msg = f"贴吧签到结束\n\n签到成功 {n_succeed} 个\n签到异常 {n_faild} 个"
        for channel in self.channels:
            try:
                channel.send(msg)
            except Exception as e:
                self.logger.error(f"[{channel.name}] 发送消息失败: {str(e)}")


if __name__ == "__main__":
    tb = Tieba("BDUSS", [
        LarkChannel("飞书 webhook"),
        WorkWechatBotChannel("企业微信机器人 key"),
    ])
    tb.run()
