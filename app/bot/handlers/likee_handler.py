import os
from pathlib import Path
from uuid import uuid4
import moviepy as mp

from app.bot.controller.like_controller import LikeeController
from app.core.extensions.utils import WORKDIR
from app.core.settings.config import get_settings

settings = get_settings()


def validate_likee_url(url: str) -> str:
    return url.split("?")[0].strip()


async def get_likee_video(url: str) -> str:
    controller = LikeeController(api_key=settings.LIKEE_API_KEY)
    video_path = controller.download_video(url)
    if not video_path or not Path(video_path).exists():
        raise Exception("❌ Likee video could not be downloaded.")
    return video_path


async def extract_audio_from_likee_video_smart(url: str) -> str:
    video_path = await get_likee_video(url)
    if not video_path or not os.path.exists(video_path):
        raise Exception("❌ Video not found.")

    video_name = Path(video_path).stem
    audio_filename = f"{video_name}.mp3"
    audio_path = WORKDIR.parent / "media" / "music" / audio_filename
    os.makedirs(audio_path.parent, exist_ok=True)

    try:
        video = mp.VideoFileClip(video_path)
        video.audio.write_audiofile(str(audio_path), logger=None)
        video.close()
        os.remove(video_path)
        return str(audio_path)
    except Exception as e:
        raise Exception(f"❌ Audio extraction failed: {str(e)}")
