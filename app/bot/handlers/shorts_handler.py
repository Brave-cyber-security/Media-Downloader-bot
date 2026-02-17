import logging
from pathlib import Path
from aiogram.types import Message, FSInputFile
from app.bot.controller.shorts_controller import YouTubeShortsController
from app.bot.extensions.clear import atomic_clear
from app.bot.keyboards.general_buttons import get_music_download_button
from app.bot.state.session_store import user_sessions

logger = logging.getLogger(__name__)


class YouTubeShortsHandler:
    def __init__(self):
        self.controller = YouTubeShortsController(
            Path.cwd() / "media" / "youtube_shorts"
        )

    async def handle(self, message: Message, url: str):
        try:
            status_msg = await message.answer("🔄 YouTube Shorts yuklab olinmoqda...")

            user_id = message.from_user.id
            user_sessions[user_id] = {"url": url}

            video_path = await self.controller.download_video(url)
            user_sessions[user_id]["video_path"] = video_path

            await status_msg.delete()
            await message.answer_video(
                FSInputFile(video_path),
                caption="✅ YouTube Shorts tayyor!",
                reply_markup=get_music_download_button("Shorts"),
            )
            await atomic_clear(video_path)

        except Exception as e:
            logger.error(f"Handler xatolik: {e}")
            await message.answer("❌ Video yuklab olishda xatolik yuz berdi")
