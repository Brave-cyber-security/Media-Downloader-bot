import logging
import asyncio
import re
import subprocess
from pathlib import Path
from pytubefix import YouTube
import yt_dlp

from app.bot.extensions.get_random_cookie import get_all_youtube_cookies
from app.core.extensions.enums import CookieType

logger = logging.getLogger(__name__)


class YouTubeShortsController:
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    async def download_video(self, url: str) -> str:
        try:
            normalized_url = self._normalize_youtube_url(url)
            return await asyncio.to_thread(self._download_with_ytdlp, normalized_url)
        except Exception as ytdlp_error:
            logger.warning("yt-dlp failed for Shorts, falling back to pytubefix")
            try:
                return await asyncio.to_thread(self._download_with_pytubefix, url)
            except Exception:
                logger.exception(f"YouTube Shorts yuklab olishda xatolik: {url}")
                raise ytdlp_error

    @staticmethod
    def _normalize_youtube_url(url: str) -> str:
        match = re.search(
            r"(?:youtube\.com/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})", url
        )
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"
        return url

    @staticmethod
    def _extractor_variants() -> list[dict]:
        return [
            {},
            {"extractor_args": {"youtube": {"player_client": ["web"]}}},
            {"extractor_args": {"youtube": {"player_client": ["mweb"]}}},
            {"extractor_args": {"youtube": {"player_client": ["android"]}}},
            {"extractor_args": {"youtube": {"player_client": ["ios"]}}},
        ]

    def _download_with_ytdlp(self, url: str) -> str:
        cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)
        cookie_candidates: list[str | None] = cookies + [None] if cookies else [None]
        last_error: Exception | None = None

        for variant in self._extractor_variants():
            for cookie_file in cookie_candidates:
                ydl_opts = {
                    "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                    "outtmpl": str(self.save_dir / "%(id)s.%(ext)s"),
                    "merge_output_format": "mp4",
                    "noplaylist": True,
                    "quiet": True,
                    "no_warnings": True,
                    "retries": 3,
                    "fragment_retries": 3,
                    "socket_timeout": 20,
                    "geo_bypass": True,
                }
                ydl_opts.update(variant)
                if cookie_file:
                    ydl_opts["cookiefile"] = cookie_file

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if not info:
                            raise ValueError("yt-dlp video ma'lumotlarini topa olmadi")

                        video_id = info.get("id")
                        prepared = Path(ydl.prepare_filename(info))
                        candidates = [prepared, prepared.with_suffix(".mp4")]
                        if video_id:
                            candidates.extend(
                                self.save_dir / f"{video_id}.{ext}"
                                for ext in ("mp4", "webm", "mkv", "mov")
                            )

                        for candidate in candidates:
                            if candidate.exists() and candidate.stat().st_size > 1024:
                                return str(self._prepare_telegram_video(candidate))

                        if video_id:
                            for candidate in sorted(
                                self.save_dir.glob(f"{video_id}.*"),
                                key=lambda p: p.stat().st_mtime,
                                reverse=True,
                            ):
                                if (
                                    candidate.exists()
                                    and candidate.stat().st_size > 1024
                                ):
                                    return str(self._prepare_telegram_video(candidate))

                        raise ValueError("Downloaded shorts file not found")
                except Exception as err:
                    last_error = err
                    logger.warning(
                        f"Shorts yt-dlp attempt failed (cookie={cookie_file}, variant={variant}): {err}"
                    )

        if last_error:
            raise last_error
        raise ValueError("YouTube Shorts yuklab olishda noma'lum xatolik")

    def _download_with_pytubefix(self, url: str) -> str:
        yt = YouTube(url)

        stream = (
            yt.streams.filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )

        if not stream:
            stream = (
                yt.streams.filter(adaptive=True, file_extension="mp4", only_video=True)
                .order_by("resolution")
                .desc()
                .first()
            )

        if not stream:
            raise ValueError("Yuklab olinadigan video topilmadi")

        filename = f"{yt.video_id}.mp4"
        filepath = self.save_dir / filename

        if filepath.exists() and filepath.stat().st_size > 1024:
            if not self._has_valid_duration(filepath):
                try:
                    filepath.unlink(missing_ok=True)
                except Exception:
                    pass
            else:
                return str(self._prepare_telegram_video(filepath))

        stream.download(output_path=str(self.save_dir), filename=filename)
        if not filepath.exists() or filepath.stat().st_size <= 1024:
            raise ValueError("Downloaded shorts file is invalid")
        return str(self._prepare_telegram_video(filepath))

    @staticmethod
    def _has_valid_duration(video_path: Path) -> bool:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return False
            duration = float((result.stdout or "0").strip() or "0")
            return duration > 0.1
        except Exception:
            return False

    def _prepare_telegram_video(self, source_path: Path) -> Path:
        if source_path.suffix.lower() == ".mp4" and source_path.stem.endswith("_tg"):
            if self._has_valid_duration(source_path):
                return source_path

        if not self._has_valid_duration(source_path):
            raise ValueError("Downloaded shorts file has invalid duration")

        target_path = source_path.with_name(f"{source_path.stem}_tg.mp4")
        if target_path.exists() and target_path.stat().st_size > 1024:
            if self._has_valid_duration(target_path):
                return target_path

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(target_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if (
            result.returncode == 0
            and target_path.exists()
            and target_path.stat().st_size > 1024
            and self._has_valid_duration(target_path)
        ):
            return target_path

        # Fallback to source if conversion is not needed and source is still valid
        if self._has_valid_duration(source_path):
            return source_path

        raise ValueError("Telegram-friendly Shorts video yaratib bo'lmadi")
