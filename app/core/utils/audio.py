from pathlib import Path
import logging
import moviepy

logger = logging.getLogger(__name__)


def extract_audio_from_video(video_path: str) -> str | None:
    try:
        video = moviepy.VideoFileClip(video_path)
        audio_path = str(Path(video_path).with_suffix(".mp3"))

        video.audio.write_audiofile(audio_path, logger=None)
        video.close()
        return audio_path
    except Exception as e:
        logger.error(f"❌ Audio extraction failed: {e}")
        return None
