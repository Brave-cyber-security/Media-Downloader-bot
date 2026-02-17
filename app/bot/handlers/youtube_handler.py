from __future__ import annotations
import asyncio
import concurrent.futures
import logging
import os
import time
from pathlib import Path
from typing import Optional
import yt_dlp

from app.bot.extensions.get_random_cookie import (
    get_random_cookie_for_youtube,
    get_all_youtube_cookies,
)
from app.bot.handlers.youtube_handler_pytube import download_audio_with_pytube
from app.core.extensions.enums import CookieType
from app.core.extensions.utils import WORKDIR

logger = logging.getLogger(__name__)

# Optimized paths and thread pool
MUSIC_DIR = WORKDIR.parent / "media" / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# Much larger thread pool for parallel downloads
_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=min(16, (os.cpu_count() or 1) * 4), thread_name_prefix="yt-dl"
)

# Improved format selection with proper fallbacks
AUDIO_OPTS_SMART = {
    # More robust format selection with better fallbacks
    "format": (
        "bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio[ext=mp3]/"
        "bestaudio[acodec=aac]/bestaudio[acodec=mp3]/bestaudio/best"
    ),
    "outtmpl": f"{MUSIC_DIR}/%(title).60s-%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "ignoreerrors": True,
    "socket_timeout": 10,
    "retries": 3,
    "fragment_retries": 3,
    "cookiefile": get_random_cookie_for_youtube(CookieType.YOUTUBE.value),
    # Add extractaudio for audio-only downloads
    "extractaudio": True,
    # Prefer free formats when available
    "prefer_free_formats": True,
}

# Improved video format selection
VIDEO_OPTS = {
    "format": (
        "bestvideo[height<=720][filesize<45M]+bestaudio[ext=m4a]/best[height<=720][filesize<45M]/"
        "bestvideo[height<=720]+bestaudio/best[height<=720]/best[filesize<45M]/best"
    ),
    "outtmpl": f"{MUSIC_DIR}/%(title).40s-%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "ignoreerrors": True,
    "socket_timeout": 15,
    "retries": 3,
    "fragment_retries": 3,
    "cookiefile": get_random_cookie_for_youtube(CookieType.YOUTUBE.value),
    "merge_output_format": "mp4",  # Ensure consistent output format
}
print("Youtube video handler: ", VIDEO_OPTS["cookiefile"])


def _get_smart_audio_opts(
    convert_to_mp3: bool = False, allow_large: bool = False
) -> dict:
    AUDIO_OPTS_SMART["cookiefile"] = get_random_cookie_for_youtube(
        CookieType.YOUTUBE.value
    )
    opts = AUDIO_OPTS_SMART.copy()

    if allow_large:
        # Remove filesize restrictions for large files
        opts["format"] = (
            "bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio[ext=mp3]/"
            "bestaudio[acodec=aac]/bestaudio[acodec=mp3]/bestaudio/best"
        )

    if convert_to_mp3:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",  # Slightly better quality
            }
        ]
        opts["postprocessor_args"] = [
            "-threads",
            str(min(4, os.cpu_count() or 1)),
            "-loglevel",
            "error",
        ]
        # Remove extractaudio when using postprocessor
        opts.pop("extractaudio", None)

    return opts


def _audio_sync(query: str) -> Optional[str]:

    cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)

    for cookie_file in cookies:
        opts = _get_smart_audio_opts()
        opts["cookiefile"] = cookie_file
        print("Trying cookie:", cookie_file)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if not info or not info.get("entries") or not info["entries"][0]:
                    logger.warning(f"No results for query: {query}")
                    continue

                entry = info["entries"][0]
                ydl.download([entry["webpage_url"]])

                file_path = Path(ydl.prepare_filename(entry))
                for ext in [".m4a", ".mp3", ".webm", ".opus"]:
                    test_file = file_path.with_suffix(ext)
                    if test_file.exists() and test_file.stat().st_size > 1000:
                        return str(test_file)

        except Exception as e:
            logger.warning(f"Cookie {cookie_file} failed: {e}")
            continue

    logger.warning(f"No valid audio file found for: {query}")
    return None


def _video_sync(video_id: str, title: str) -> Optional[str]:
    cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)

    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40]

    for cookie_file in cookies:
        opts = VIDEO_OPTS.copy()
        opts["cookiefile"] = cookie_file
        print("Trying cookie:", cookie_file)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                url = f"https://youtube.com/watch?v={video_id}"
                ydl.download([url])

                base_patterns = [
                    f"{safe_title}-{video_id}",
                    f"*{video_id}*",
                    f"{safe_title}*",
                ]

                for pattern in base_patterns:
                    for ext in ("mp4", "webm", "mkv", "avi"):
                        for file_path in MUSIC_DIR.glob(f"{pattern}.{ext}"):
                            if file_path.exists() and file_path.stat().st_size > 1000:
                                return str(file_path)
        except Exception as e:
            logger.warning(f"Video download failed with {cookie_file}: {e}")
            continue

    logger.error(f"All cookies failed for video: {video_id}")
    return None


# Faster async wrappers with improved error handling
async def download_music_from_youtube(title: str, artist: str) -> str | None:
    """Audio download using pytubefix."""
    if not title or not artist:
        return None

    query = f"{title} {artist}"
    loop = asyncio.get_running_loop()

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, download_audio_with_pytube, query),
            timeout=60,
        )
    except asyncio.TimeoutError:
        logger.warning(f"Audio download timeout: {query}")
        return None
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        return None


async def download_video_from_youtube(video_id: str, title: str) -> Optional[str]:
    """Fast video download with improved error handling and fallbacks."""
    if not video_id or not title:
        return None

    loop = asyncio.get_running_loop()

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_pool, _video_sync, video_id, title),
            timeout=90,  # Increased timeout for video downloads
        )
    except asyncio.TimeoutError:
        logger.warning(f"Video timeout: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Video error: {e}")
        return None


async def cleanup_old_files(max_age: int = 1800) -> None:
    """Enhanced cleanup for all supported formats."""
    if not MUSIC_DIR.exists():
        return

    now = time.time()
    files_to_delete = []

    try:
        # Support all possible audio and video formats
        patterns = [
            "*.m4a",
            "*.mp3",
            "*.aac",
            "*.opus",
            "*.webm",
            "*.mp4",
            "*.mkv",
            "*.avi",
            "*.flv",
            "*.ogg",
            "*.wav",
        ]

        for pattern in patterns:
            for file_path in MUSIC_DIR.glob(pattern):
                if file_path.is_file() and now - file_path.stat().st_mtime > max_age:
                    files_to_delete.append(file_path)

        # Batch delete with better error handling
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink(missing_ok=True)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Could not delete {file_path.name}: {e}")
                continue

        if deleted_count > 0:
            logger.info(f"Cleaned {deleted_count}/{len(files_to_delete)} files")

    except Exception as e:
        logger.error(f"Cleanup error: {e}")


async def shutdown_downloader() -> None:
    """Graceful shutdown."""
    _pool.shutdown(wait=False)
