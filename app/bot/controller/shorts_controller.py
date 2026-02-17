import logging
import asyncio
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
            return await asyncio.to_thread(self._download_with_ytdlp, url)
        except Exception as ytdlp_error:
            logger.warning("yt-dlp failed for Shorts, falling back to pytubefix")
            try:
                return await asyncio.to_thread(self._download_with_pytubefix, url)
            except Exception:
                logger.exception(f"YouTube Shorts yuklab olishda xatolik: {url}")
                raise ytdlp_error

    def _download_with_ytdlp(self, url: str) -> str:
        cookies = get_all_youtube_cookies(CookieType.YOUTUBE.value)
        cookie_candidates: list[str | None] = cookies if cookies else [None]
        last_error: Exception | None = None

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
                "socket_timeout": 15,
            }
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
                            return str(candidate)

                    if video_id:
                        for candidate in sorted(
                            self.save_dir.glob(f"{video_id}.*"),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        ):
                            if candidate.exists() and candidate.stat().st_size > 1024:
                                return str(candidate)

                    raise ValueError("Downloaded shorts file not found")
            except Exception as err:
                last_error = err
                logger.warning(f"Shorts yt-dlp attempt failed (cookie={cookie_file}): {err}")

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
            return str(filepath)

        stream.download(output_path=str(self.save_dir), filename=filename)
        if not filepath.exists() or filepath.stat().st_size <= 1024:
            raise ValueError("Downloaded shorts file is invalid")
        return str(filepath)
