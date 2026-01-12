import requests

# 设置你的 API 密钥
API_KEY = "YOUR_API_KEY"
url = "https://api.deepseek.com/chat/completions"

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# 请求体：通过 system 和 user 消息描述编程任务
data = {
    "model": "deepseek-chat",  # 可替换为 deepseek-reasoner 或 deepseek-coder
    "messages": [
        {
            "role": "system",
            "content": "你是一个专业的代码助手，擅长用Python解决问题。"  # 设定助手角色
        },
        {
            "role": "user",
            "content": "请用Python写一个函数，快速计算斐波那契数列的第n项。"  # 具体代码任务
        }
    ],
    "stream": False  # 流式输出，长响应时建议设为 True
}

# 发送请求
response = requests.post(url, headers=headers, json=data)

# 解析并打印结果
if response.status_code == 200:
    result = response.json()
    generated_code = result['choices'][0]['message']['content']
    print(generated_code)
else:
    print("请求失败，状态码:", response.status_code)
    print(response.text)