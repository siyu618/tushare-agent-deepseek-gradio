import os
import requests
from twisted.spread.pb import respond

DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")


class DeepSeekClient:
    def __init__(self, url: str = None, api_key: str = None):
        self.url = url or DEEPSEEK_API_URL
        self.api_key = api_key or DEEPSEEK_API_KEY
        if not self.url:
            raise ValueError("DEEPSEEK_API_URL is not set")


    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
        """Call DeepSeek inference endpoint. Adjust payload to your DeepSeek API spec."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = requests.post(self.url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Expecting data contains 'text' or similar key — adapt to your DeepSeek response schema
        if isinstance(data, dict):
            return data.get("text") or data.get("output") or str(data)
        return str(data)

    def chat(self, messages):
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": messages}
        resp = requests.post(self.url, headers=headers, json=payload, timeout=60)
        print(headers, payload)
        print("resp.text = ", resp.text)
        print("""resp.json()["choices"][0]["message"]["content"]""", resp.json()["choices"][0]["message"]["content"])
        return resp.json()["choices"][0]["message"]["content"]