import logging
from aiogram import types
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo
from aiogram.exceptions import TelegramBadRequest
from app.bot.controller.threads_controller import ThreadsController
from aiogram.utils.i18n import gettext as _
from pathlib import Path
import re
from typing import List, Optional

from app.core.utils.audio import extract_audio_from_video

logger = logging.getLogger(__name__)


class ThreadHandler:
    def __init__(self):
        self.controller = None
        self.download_path = Path.cwd().parent / "media" / "threads"

    def _init_controller(self):
        if not self.controller:
            self.controller = ThreadsController(self.download_path)

    def _cleanup_controller(self):
        if self.controller:
            self.controller.close()
            self.controller = None

    def _is_valid_threads_url(self, url: str) -> bool:
        patterns = [
            r"https?://(?:www\.)?threads\.com/[@\w\.-]+/post/[\w\.-]+",
            r"https?://(?:www\.)?threads\.com/t/[\w\.-]+",
            r"https?://(?:www\.)?threads\.com/[\w\.-]+/[\w\.-]+",
        ]
        return any(re.match(pattern, url) for pattern in patterns)

    async def handle_threads_url(self, message: types.Message, url: str) -> None:
        try:
            if not self._is_valid_threads_url(url):
                await message.reply(
                    _("threads_invalid_url")
                    or "❌ Noto'g'ri Threads URL!\n"
                    "Masalan: https://threads.com/@username/post/abc123"
                )
                return

            loading_msg = await message.reply(
                _("threads_loading") or "🔄 Threads post tahlil qilinmoqda..."
            )

            self._init_controller()
            result = await self.controller.download_media(url)

            if not result["success"]:
                await loading_msg.edit_text(result["message"])
                return

            downloaded_files = result["downloaded_files"]
            failed_files = result.get("failed_files", [])

            await loading_msg.edit_text(
                _("threads_sending_files").format(count=len(downloaded_files))
                or f"✅ {len(downloaded_files)} ta fayl yuklandi!\n📤 Yuborilmoqda..."
            )

            await self._send_media_files(message, downloaded_files)

            success_text = _("threads_success").format(
                total=len(downloaded_files), failed=len(failed_files)
            )

            await loading_msg.edit_text(success_text)

        except Exception as e:
            logger.error(f"Threads handle error: {e}")
            await message.reply(_("threads_error") or f"❌ Xatolik: {str(e)}")
        finally:
            self._cleanup_controller()

    async def _send_media_files(
        self, message: types.Message, files: List[dict]
    ) -> None:
        if not files:
            await message.reply(_("threads_no_files") or "❌ Fayllar topilmadi.")
            return

        images = [f for f in files if f["type"] == "image"]
        videos = [f for f in files if f["type"] == "video"]

        if images:
            await self._send_image_group(message, images)
        if videos:
            await self._send_videos(message, videos)

    async def _send_image_group(
        self, message: types.Message, images: List[dict]
    ) -> None:
        try:
            if len(images) == 1:
                path = Path(images[0]["path"])
                if path.exists():
                    await message.reply_photo(FSInputFile(path))
            else:
                media_group = []
                for img in images[:10]:
                    path = Path(img["path"])
                    if path.exists():
                        media_group.append(InputMediaPhoto(media=FSInputFile(path)))
                if media_group:
                    await message.reply_media_group(media_group)
                if len(images) > 10:
                    await self._send_image_group(message, images[10:])
        except Exception as e:
            logger.warning(f"Image group error: {e}")
            for img in images:
                try:
                    path = Path(img["path"])
                    if path.exists():
                        await message.reply_photo(FSInputFile(path))
                except Exception as inner:
                    logger.warning(f"Single image error: {inner}")

    async def _send_videos(self, message: types.Message, videos: List[dict]) -> None:
        try:
            for video in videos:
                path = Path(video["path"])
                if not path.exists():
                    logger.warning(f"Video path not found: {path}")
                    await message.reply(f"❌ Video fayl topilmadi: {path}")
                    continue

                size = path.stat().st_size
                if size > 50 * 1024 * 1024:
                    await message.reply(
                        _("threads_video_too_large").format(
                            name=video["filename"],
                            size=round(size / (1024 * 1024), 1),
                            path=path,
                        )
                    )
                    continue

                try:
                    video_file = FSInputFile(path)
                    await message.reply_video(video_file)
                except TelegramBadRequest as e:
                    logger.warning(f"Telegram video error: {e}")
                    if "video format not supported" in str(e).lower():
                        await message.reply_document(video_file)
                    else:
                        await message.reply(f"❌ Telegram xatolik: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error sending video: {e}")
                    await message.reply(_("threads_video_send_error") + f"\n{str(e)}")
        except Exception as e:
            logger.error(f"Video loop outer error: {e}")
            await message.reply(_("threads_video_send_error"))

    async def get_single_video_from_url(self, url: str) -> Optional[str]:
        self._init_controller()
        result = await self.controller.download_media(url)
        self._cleanup_controller()

        if result["success"] and result["downloaded_files"]:
            # Faqat birinchi videoni olamiz
            for file in result["downloaded_files"]:
                if file["type"] == "video":
                    return file["path"]
        return None

    async def extract_audio(self, video_path: str) -> Optional[str]:
        return extract_audio_from_video(video_path)
