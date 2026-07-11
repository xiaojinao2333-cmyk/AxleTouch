import json

from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

PROVIDER_CONFIGS = {
    "stepfun": {
        "name": "阶跃星辰",
        "base_url": "https://api.stepfun.com/step_plan/v1",
        "default_model": "step-3.7-flash",
    },
    "bailian": {
        "name": "阿里百炼",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-turbo",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
}

def Client_creater(config):
    return AIClient(config.get("provider", "stepfun"), config.get("api_key", ""))


class AIClient(QNetworkAccessManager):

    response_ready = pyqtSignal(str)

    def __init__(self, provider, api_key):
        super().__init__()
        self._provider = provider
        self._api_key = api_key
        self._messages = []

    @property
    def _cfg(self):
        return PROVIDER_CONFIGS.get(self._provider, PROVIDER_CONFIGS["stepfun"])

    def set_system_prompt(self, prompt):
        self._messages = [{"role": "system", "content": prompt}]

    def update(self, provider, api_key):
        self._provider = provider
        self._api_key = api_key
        self._messages = [self._messages[0]] if self._messages else []

    def send_message(self, user_message):
        self._messages.append({"role": "user", "content": user_message})
        self._do_request()

    def _do_request(self):
        if not self._api_key:
            self.response_ready.emit("呜...还没设置 API Key 呢！去设置里填一下啦笨蛋~")
            return

        body = {
            "model": self._cfg["default_model"],
            "messages": self._messages,
            "temperature": 1,
            "stream": False
        }
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = QNetworkRequest(QUrl(f"{self._cfg['base_url']}/chat/completions"))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        req.setRawHeader(b"Authorization", f"Bearer {self._api_key}".encode())
        reply = self.post(req, raw)
        reply.finished.connect(lambda r=reply: self._on_reply(r))

    def _on_reply(self, reply):
        try:
            if reply.error() != QNetworkReply.NoError:
                self.response_ready.emit(f"呜...网络错误: {reply.errorString()}")
                reply.deleteLater()
                return

            raw = reply.readAll().data().decode()
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            self._messages.append({"role": "assistant", "content": content})
            self.response_ready.emit(content)
        except Exception as e:
            self.response_ready.emit(f"呜...解析失败: {e}")
        finally:
            reply.deleteLater()