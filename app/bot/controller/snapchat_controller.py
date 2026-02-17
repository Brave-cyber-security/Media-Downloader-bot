import time
import base64
import logging
import requests
from pathlib import Path
from uuid import uuid4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


class SnapchatController:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")

        self.driver = webdriver.Chrome(
            service=Service("/usr/bin/chromedriver"), options=chrome_options
        )

    def download_snapchat_video(self, url: str, save_dir: Path) -> str | None:
        try:
            self.driver.get(url)
            time.sleep(5)

            video_element = self.driver.find_element(By.TAG_NAME, "video")
            video_url = video_element.get_attribute("src")

            if not video_url:
                logger.error("❌ No video URL found.")
                return None

            response = requests.get(video_url, stream=True)
            if response.status_code != 200:
                logger.error("❌ Failed to fetch video content.")
                return None

            filename = f"{uuid4().hex}.mp4"
            file_path = save_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return str(file_path)

        except Exception as e:
            logger.error(f"Snapchat download error: {e}")
            return None
        finally:
            self.driver.quit()
