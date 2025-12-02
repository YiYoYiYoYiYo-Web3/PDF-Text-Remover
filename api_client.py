import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class APIClient:
    def __init__(self):
        """Initialize API client with environment variables."""
        self.base_url = os.getenv('IMAGE_API_BASE', 'http://localhost:8000/v1/chat/completions')
        api_key = os.getenv('IMAGE_API_KEY', 'han1234')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def process_image(self, image_base64, prompt="Remove all text and garbled Text from this image, keeping the background and other elements exactly the same."):
        data = {
            "model": "gemini-3.0-pro-image-landscape", # Using the landscape model as default
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "stream": True
        }

        print("[IMAGE API] Sending request to API...")
        try:
            response = requests.post(self.base_url, headers=self.headers, json=data, stream=True)
            
            if response.status_code != 200:
                print(f"[IMAGE API] Error: {response.status_code} - {response.text}")
                return None

            full_content = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]
                        if json_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(json_str)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_content += content
                        except json.JSONDecodeError:
                            pass
            
            return full_content

        except Exception as e:
            print(f"[IMAGE API] Exception during API call: {e}")
            return None
