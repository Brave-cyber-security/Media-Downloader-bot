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
    get_all_youtube_cookies,
)
from app.bot.handlers.youtube_handler_pytube import download_audio_with_pytube
from app.core.extensions.enums import CookieType
from app.core.extensions.utils import WORKDIR

logger = logging.getLogger(__name__)

MUSIC_DIR = WORKDIR.parent / "media" / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=min(16, (os.cpu_count() or 1) * 4), thread_name_prefix="yt-dl"
)


class _YtDlpSilentLogger:
    def debug(self, msg):
        return

    def warning(self, msg):
        return

    def error(self, msg):
        return


AUDIO_OPTS_BASE = {
    "outtmpl": f"{MUSIC_DIR}/%(title).60s-%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "ignoreerrors": False,
    "socket_timeout": 12,
    "retries": 3,
    "fragment_retries": 3,
    "logger": _YtDlpSilentLogger(),
    "prefer_free_formats": True,
    "extractor_args": {"youtube": {"player_client": ["web", "mweb"]}},
    "geo_bypass": True,
}

VIDEO_OPTS = {
    "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "outtmpl": f"{MUSIC_DIR}/%(title).40s-%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "ignoreerrors": False,
    "socket_timeout": 15,
    "retries": 3,
    "fragment_retries": 3,
    "merge_output_format": "mp4",
    "logger": _YtDlpSilentLogger(),
    "extractor_args": {"youtube": {"player_client": ["web", "mweb"]}},
    "geo_bypass": True,
}


def _get_smart_audio_opts(
    format_selector: str, cookie_file: str | None, convert_to_mp3: bool = True
) -> dict:
    opts = AUDIO_OPTS_BASE.copy()
    opts["format"] = format_selector

    if cookie_file:
        opts["cookiefile"] = cookie_file

    if convert_to_mp3:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
        opts["postprocessor_args"] = [
            "-threads",
            str(min(4, os.cpu_count() or 1)),
            "-loglevel",
            "error",
        ]

    return opts


def _find_downloaded_file(base_path: Path) -> Optional[str]:
    for ext in [".mp3", ".m4a", ".webm", ".opus", ".aac"]:
        candidate = base_path.with_suffix(ext)
        if candidate.exists() and candidate.stat().st_size > 1000:
            return str(candidate)
    return None


def _audio_sync(query: str) -> Optional[str]:
    cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)
    # Try without cookies first, then with cookies
    cookie_candidates: list[str | None] = [None] + cookies
    format_candidates = [
        "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best",
        "bestaudio/best",
        "ba/b",
    ]

    for cookie_file in cookie_candidates:
        for format_selector in format_candidates:
            opts = _get_smart_audio_opts(format_selector, cookie_file, convert_to_mp3=True)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                    if not info or not info.get("entries") or not info["entries"][0]:
                        continue

                    entry = info["entries"][0]
                    entry_url = entry.get("webpage_url") or (
                        f"https://youtube.com/watch?v={entry.get('id', '')}"
                    )
                    if not entry_url:
                        continue

                    downloaded = ydl.extract_info(entry_url, download=True)
                    effective = downloaded or entry
                    prepared = Path(ydl.prepare_filename(effective))

                    found = _find_downloaded_file(prepared)
                    if found:
                        return found

                    if effective.get("id"):
                        for candidate in sorted(
                            MUSIC_DIR.glob(f"*{effective['id']}*"),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        ):
                            if candidate.is_file() and candidate.stat().st_size > 1000:
                                return str(candidate)

            except Exception as e:
                error_text = str(e).lower()
                if "requested format is not available" in error_text:
                    continue
                logger.warning(
                    f"Audio download failed (cookie={cookie_file}, format={format_selector}): {e}"
                )
                continue

    logger.warning(f"No valid audio file found for: {query}")
    return None


def _video_sync(video_id: str, title: str) -> Optional[str]:
    cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)
    # Try without cookies first, then with cookies
    cookie_candidates: list[str | None] = [None] + cookies

    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40]

    format_candidates = [
        "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "bv*[height<=720]+ba/b[height<=720]/b",
        "best",
        "18",
    ]

    for cookie_file in cookie_candidates:
        for format_selector in format_candidates:
            opts = VIDEO_OPTS.copy()
            opts["format"] = format_selector
            if cookie_file:
                opts["cookiefile"] = cookie_file

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
                error_text = str(e).lower()
                if "requested format is not available" in error_text:
                    continue
                logger.warning(f"Video download failed (cookie={cookie_file}, format={format_selector}): {e}")
                continue

    logger.error(f"All cookies failed for video: {video_id}")
    return None


def _video_sync_with_quality(video_id: str, title: str, quality: int) -> Optional[str]:
    cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)
    # Try without cookies first, then with cookies
    cookie_candidates: list[str | None] = [None] + cookies
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40] or video_id
    quality = min(1080, max(480, int(quality)))

    format_candidates = [
        f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best",
        f"bv*[height<={quality}]+ba/b[height<={quality}]/b",
        f"best[height<={quality}]/best",
        "best",
        "18",
    ]

    for cookie_file in cookie_candidates:
        for format_selector in format_candidates:
            opts = VIDEO_OPTS.copy()
            opts["format"] = format_selector
            if cookie_file:
                opts["cookiefile"] = cookie_file
            else:
                opts.pop("cookiefile", None)

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
                error_text = str(e).lower()
                if "requested format is not available" in error_text:
                    continue
                logger.warning(
                    f"Video download failed (video_id={video_id}, q={quality}, cookie={cookie_file}, format={format_selector}): {e}"
                )
                continue

    logger.error(f"All video quality attempts failed for video: {video_id}, q={quality}")
    return None


async def download_music_from_youtube(title: str, artist: str) -> str | None:
    """Audio download using yt-dlp + cookies, pytubefix fallback."""
    if not title or not artist:
        return None

    query = f"{title} {artist}"
    loop = asyncio.get_running_loop()

    try:
        file_path = await asyncio.wait_for(
            loop.run_in_executor(_pool, _audio_sync, query),
            timeout=90,
        )
        if file_path:
            return file_path

        return await asyncio.wait_for(
            loop.run_in_executor(None, download_audio_with_pytube, query),
            timeout=30,
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
            timeout=90,
        )
    except asyncio.TimeoutError:
        logger.warning(f"Video timeout: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Video error: {e}")
        return None


async def download_video_from_youtube_with_quality(
    video_id: str, title: str, quality: int
) -> Optional[str]:
    if not video_id or not title:
        return None

    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_pool, _video_sync_with_quality, video_id, title, quality),
            timeout=90,
        )
    except asyncio.TimeoutError:
        logger.warning(f"Video timeout (quality={quality}): {video_id}")
        return None
    except Exception as e:
        logger.error(f"Video quality error (quality={quality}): {e}")
        return None


async def cleanup_old_files(max_age: int = 1800) -> None:
    """Enhanced cleanup for all supported formats."""
    if not MUSIC_DIR.exists():
        return

    now = time.time()
    files_to_delete = []

    try:
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
