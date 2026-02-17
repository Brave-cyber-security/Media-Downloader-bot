import os
import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4
import logging

from yt_dlp import YoutubeDL
from app.bot.extensions.get_random_cookie import get_random_cookie_for_instagram
from app.core.extensions.enums import CookieType
from app.core.extensions.utils import WORKDIR, logger


async def download_instagram_video_only_mp4(url: str, target_folder=None) -> str:
    """Instagram video downloader - improved path handling"""

    if target_folder is None:
        target_folder = WORKDIR.parent / "media" / "instagram"

    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)

    filename = str(uuid4())
    output_template = str(target_folder / f"{filename}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cookiefile": get_random_cookie_for_instagram(CookieType.INSTAGRAM.value),
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            await asyncio.get_event_loop().run_in_executor(None, ydl.download, [url])

        # Find the downloaded file
        for file in target_folder.glob(f"{filename}.*"):
            if file.suffix in [".mp4", ".webm", ".mkv", ".mov"]:
                logger.info(f"Instagram video downloaded: {file}")
                return str(file)

        raise Exception("Downloaded file not found")

    except Exception as e:
        logger.error(f"Instagram download error: {e}")

        raise Exception(
            f"Instagram yuklab olishda xatolik: {str(e)}, cookie: {ydl_opts['cookiefile']}"
        )


def validate_instagram_url(url: str) -> str:
    """URL validation and cleanup"""
    clean_url = url.split("?")[0].strip().rstrip("/")

    if not clean_url.startswith("http"):
        clean_url = "https://" + clean_url

    if "/reel/" in clean_url or "/p/" in clean_url or "/tv/" in clean_url:
        return clean_url + "/"

    return clean_url


async def download_instagram_for_group(url: str) -> dict:
    """Group uchun Instagram downloader"""
    try:
        clean_url = validate_instagram_url(url)
        file_path = await download_instagram_video_only_mp4(clean_url)

        if file_path and Path(file_path).exists():
            return {
                "success": True,
                "message": "✅ Instagram video yuklandi",
                "files": [{"type": "video", "path": file_path}],
            }
        else:
            return {
                "success": False,
                "message": "❌ Instagram video yuklanmadi",
                "files": [],
            }

    except Exception as e:
        logger.error(f"Instagram group download error: {e}")
        return {
            "success": False,
            "message": f"❌ Instagram xatolik: {str(e)[:100]}",
            "files": [],
        }


async def extract_audio_simple(video_path: str) -> str:
    """Audio extraction - re-download if file missing"""

    try:
        video_file = Path(video_path)
        logger.info(f"Trying to extract audio from: {video_file}")

        # Check if video file exists
        if not video_file.exists():
            logger.warning(f"Video file missing: {video_file}")
            # Video fayl yo'q bo'lsa, error berish o'rniga URL dan qayta yuklab olamiz
            raise Exception(f"Video fayl topilmadi. Qayta urinib ko'ring.")

        # Check file size
        if video_file.stat().st_size == 0:
            logger.error(f"Video file is empty: {video_file}")
            raise Exception("Video fayl bo'sh")

        logger.info(f"Video file found, size: {video_file.stat().st_size} bytes")

        # Create audio directory
        audio_dir = WORKDIR.parent / "media" / "music"
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_filename = f"{video_file.stem}.mp3"
        audio_path = audio_dir / audio_filename

        # Try FFmpeg first (faster)
        if await extract_with_ffmpeg(str(video_file), str(audio_path)):
            logger.info(f"Audio extracted with FFmpeg: {audio_path}")
            return str(audio_path)

        # Fallback to yt-dlp
        logger.info("FFmpeg failed, trying yt-dlp...")
        return await extract_with_ytdlp(str(video_file), str(audio_path))

    except Exception as e:
        logger.error(f"Audio extraction error: {e}")
        raise Exception(f"Audio ajratishda xatolik: {str(e)}")


async def extract_with_ffmpeg(video_path: str, audio_path: str) -> bool:
    """Extract audio using FFmpeg"""
    try:
        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "mp3",
            "-ab",
            "192k",
            "-ar",
            "44100",
            "-y",
            audio_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0 and Path(audio_path).exists():
            return True

        logger.warning(
            f"FFmpeg failed: {stderr.decode() if stderr else 'Unknown error'}"
        )
        return False

    except Exception as e:
        logger.warning(f"FFmpeg extraction failed: {e}")
        return False


async def extract_with_ytdlp(video_path: str, audio_path: str) -> str:
    """Extract audio using yt-dlp as fallback"""

    try:
        audio_dir = Path(audio_path).parent
        filename_base = Path(audio_path).stem

        ydl_opts = {
            "outtmpl": str(audio_dir / f"{filename_base}.%(ext)s"),
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            await asyncio.get_event_loop().run_in_executor(
                None, ydl.extract_info, video_path, {"extract_flat": False}
            )

        # Find the extracted audio file
        for audio_file in audio_dir.glob(f"{filename_base}.*"):
            if audio_file.suffix == ".mp3":
                logger.info(f"Audio extracted with yt-dlp: {audio_file}")
                return str(audio_file)

        raise Exception("yt-dlp audio extraction failed")

    except Exception as e:
        logger.error(f"yt-dlp extraction error: {e}")
        raise Exception(f"yt-dlp bilan audio ajratish xatoligi: {str(e)}")


# Legacy functions for compatibility
async def extract_audio_from_instagram_video(url: str) -> str:
    """Legacy function - downloads video first then extracts audio"""
    try:
        video_path = await download_instagram_video_only_mp4(url)
        audio_path = await extract_audio_simple(video_path)

        # Clean up video file
        try:
            Path(video_path).unlink()
        except:
            pass

        return audio_path

    except Exception as e:
        raise Exception(f"Audio extraction from URL failed: {str(e)}")


async def extract_audio_from_instagram_video_smart(url: str) -> str:
    """Smart audio extraction - same as legacy for compatibility"""
    return await extract_audio_from_instagram_video(url)
