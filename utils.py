import base64
from io import BytesIO
import re
import requests
from PIL import Image

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def base64_to_image(base64_str):
    return Image.open(BytesIO(base64.b64decode(base64_str)))

def extract_url_from_text(text):
    # Find http/https urls
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    if urls:
        # Clean up markdown syntax if present (e.g. closing parenthesis)
        url = urls[0]
        if url.endswith(')'):
            url = url[:-1]
        return url
    return None

def download_image_from_url(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"Error downloading image: {e}")
    return None
