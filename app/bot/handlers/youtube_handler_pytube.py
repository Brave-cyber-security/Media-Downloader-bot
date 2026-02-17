from pytubefix import Search, YouTube
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
        videos = search.videos
        if not videos:
            logger.warning(f"No results for query: {query}")
            return None

        video_url = videos[0].watch_url
        video_id = videos[0].video_id

        # Try WEB with PoToken first, then ANDROID fallback
        clients_to_try = [
            {"client": "WEB", "use_po_token": True},
            {"client": "ANDROID"},
            {"client": "IOS"},
        ]

        for client_opts in clients_to_try:
            try:
                yt = YouTube(video_url, **client_opts)
                stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()

                if not stream:
                    continue

                title = sanitize_filename(yt.title)
                file_name = f"{title[:50]}-{video_id}.mp4"
                out_path = MUSIC_DIR / file_name

                if out_path.exists() and out_path.stat().st_size > 1024:
                    logger.info(f"File already exists: {out_path.name}")
                    return str(out_path)

                stream.download(output_path=str(MUSIC_DIR), filename=out_path.name)

                if out_path.exists() and out_path.stat().st_size > 1024:
                    logger.info(f"Downloaded audio: {out_path.name}")
                    return str(out_path)
            except Exception as e:
                logger.warning(f"pytubefix {client_opts} failed for '{query}': {e}")
                continue

        logger.error(f"All pytubefix clients failed for '{query}'")
        return None

    except Exception as e:
        logger.error(f"pytubefix download error for '{query}': {e}")
        return None
