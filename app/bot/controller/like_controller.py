import os
import requests
from uuid import uuid4
from typing import Optional
from app.core.extensions.utils import WORKDIR


class LikeeController:
    BASE_URL = "https://likee-downloader-download-likee-videos.p.rapidapi.com/process"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "likee-downloader-download-likee-videos.p.rapidapi.com",
        }

    def _generate_filename(self, url: str, data: dict) -> str:
        nick_name = data.get("nick_name", "video").replace(" ", "_")
        video_id = url.strip("/").split("/")[-1] or str(uuid4())
        return f"{nick_name}_{video_id}.mp4"

    def download_video(self, video_url: str) -> Optional[str]:
        try:
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params={"url": video_url},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            download_url = (
                data.get("withoutWater") or data.get("video_url") or data.get("url")
            )
            if not download_url:
                return None

            filename = self._generate_filename(video_url, data)
            output_dir = WORKDIR.parent / "media" / "likee"
            os.makedirs(output_dir, exist_ok=True)
            filepath = output_dir / filename

            video_response = requests.get(download_url, stream=True, timeout=30)
            video_response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return str(filepath)

        except Exception as e:
            print(f"❌ LikeeController error: {e}")
            return None
