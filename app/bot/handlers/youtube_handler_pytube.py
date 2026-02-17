from pytubefix import Search
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# Media/music katalogi
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MUSIC_DIR = BASE_DIR / "media" / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " -_").rstrip()


def download_audio_with_pytube(query: str) -> str | None:
    try:
        search = Search(query)
        if not search.results:
            logger.warning(f"No results for query: {query}")
            return None

        video = search.results[0]
        stream = video.streams.filter(only_audio=True).order_by("abr").desc().first()

        if not stream:
            logger.warning(f"No audio stream found for query: {query}")
            return None

        title = sanitize_filename(video.title)
        file_name = f"{title[:50]}-{video.video_id}.mp4"
        out_path = MUSIC_DIR / file_name

        if out_path.exists() and out_path.stat().st_size > 1024:
            logger.info(f"File already exists: {out_path.name}")
            return str(out_path)

        stream.download(output_path=str(MUSIC_DIR), filename=out_path.name)

        if out_path.exists() and out_path.stat().st_size > 1024:
            logger.info(f"Downloaded audio: {out_path.name}")
            return str(out_path)
        else:
            logger.warning(
                f"Downloaded file is too small or not found: {out_path.name}"
            )
            return None

    except Exception as e:
        logger.error(f"pytubefix download error for '{query}': {e}")
        return None
