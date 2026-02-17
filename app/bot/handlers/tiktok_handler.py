from uuid import uuid4
import os
from pathlib import Path

import moviepy

from app.bot.controller.tiktok_controller import TikTokDownloader
from app.core.extensions.utils import WORKDIR


def validate_tiktok_url(url: str) -> str:
    base_url = url.split("?")[0].strip().rstrip("/")
    parts = base_url.split("/")
    if len(parts) >= 6 and "tiktok.com" in parts:
        for i in range(len(parts)):
            if parts[i].startswith("@") and i + 2 < len(parts):
                if parts[i + 1] == "video":
                    username = parts[i]
                    video_id = parts[i + 2]
                    return f"https://www.tiktok.com/{username}/video/{video_id}"
    return base_url


async def get_tiktok_video(url: str) -> str:
    download_path = WORKDIR.parent / "media" / "tiktok"
    filename = str(uuid4())
    with TikTokDownloader(headless=True) as downloader:
        video_path = downloader.download_video(url, str(download_path), filename)
        if not video_path:
            raise Exception("❌ TikTok video could not be downloaded (returned None)")
        return video_path


async def extract_audio_from_tiktok_video_smart(url: str) -> str:
    video_path = await get_tiktok_video(url)

    if not video_path or not os.path.exists(video_path):
        raise Exception("❌ Video yuklanmadi yoki fayl mavjud emas")

    video_name = Path(video_path).stem
    audio_filename = f"{video_name}.mp3"
    audio_path = str(WORKDIR.parent / "media" / "music" / audio_filename)

    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    try:
        video = moviepy.VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_path, logger=None)

        audio.close()
        video.close()
        os.remove(video_path)

        return audio_path
    except Exception as e:
        raise Exception(f"❌ Audio extraction failed: {str(e)}")
