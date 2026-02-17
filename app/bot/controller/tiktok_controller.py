import yt_dlp
import os
import re
import time

from app.bot.extensions.get_random_cookie import get_random_cookie_for_instagram
from app.core.extensions.enums import CookieType
from app.core.extensions.utils import WORKDIR


class TikTokDownloader:
    def __init__(self, headless=True):
        self.headless = headless
        self.save_path = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _extract_video_id(self, url):
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)
        return str(int(time.time()))

    def _generate_filename(self, url, custom_name=None):
        if custom_name:
            return f"{custom_name}.mp4"
        return f"tiktok_{self._extract_video_id(url)}.mp4"

    def download_video(self, url, save_path: str, filename: str = None) -> str | None:
        os.makedirs(save_path, exist_ok=True)
        output_path = os.path.join(save_path, self._generate_filename(url, filename))

        ydl_opts = {
            "outtmpl": output_path,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": False,  # Debug uchun False
            "noplaylist": True,
            "cookiefile": get_random_cookie_for_instagram(CookieType.TIKTOK.value),
            "verbose": True,  # Debug loglar uchun
        }

        try:
            print(f"📥 Downloading TikTok video: {url}")
            print(f"📁 Output path: {output_path}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return output_path if os.path.exists(output_path) else None
        except Exception as e:
            print(f"❌ TikTok download error: {e}")
            return None
