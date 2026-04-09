import sys
import json
import requests
from pathlib import Path
from web_app_v5_vostok import DocumentAnalyzerVostok

def test_api():
    analyzer = DocumentAnalyzerVostok()
    file_path = Path("Перед 0/Isxodnie_documenti/Анализ пакета 1/Раздел_ПД№3_МКД-0109-2024-ПИР-АР_вер.01 (2).pdf")
    
    # We will hook requests.post to print the payload if it fails
    original_post = requests.post
    
    def hooked_post(url, **kwargs):
        print("Sending to URL:", url)
        try:
            resp = original_post(url, **kwargs)
            if resp.status_code == 400:
                print("GOT 400! RESPONSE:", resp.text)
                with open("failed_payload.json", "w") as f:
                    json.dump(kwargs.get('json'), f, ensure_ascii=False, indent=2)
                print("Payload dumped to failed_payload.json")
            return resp
        except Exception as e:
            print("EXCEPTION:", e)
            raise e
            
    requests.post = hooked_post
    analyzer.apiUrl = "http://192.168.47.22:1234/v1/chat/completions"
    
    res = analyzer.analyze(file_path, file_path.name)
    print("Result:", res.get("kb_hit"), res.get("title"))

if __name__ == '__main__':
    test_api()
