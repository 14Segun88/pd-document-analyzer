import requests

payload = {
    "model": "mistralai/ministral-3-14b-reasoning",
    "messages": [
        {"role": "system", "content": "You are a test system."},
        {"role": "user", "content": "Hello"}
    ],
    "temperature": 0.05,
    "max_tokens": 800
}

try:
    r = requests.post("http://192.168.47.22:1234/v1/chat/completions", json=payload, timeout=30)
    print("STATUS:", r.status_code)
    print(r.text)
except Exception as e:
    print(e)
