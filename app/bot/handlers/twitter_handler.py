import logging
from pathlib import Path
from aiogram.types import Message, FSInputFile
from aiogram.utils.i18n import gettext as _

from app.bot.controller.twitter_controller import TwitterController
from app.bot.extensions.clear import atomic_clear
from app.bot.keyboards.general_buttons import get_music_download_button

logger = logging.getLogger(__name__)
user_sessions = {}  # ⚠️ Lokal sessiya saqlovchi


class TwitterHandler:
    def __init__(self):
        self.controller = TwitterController(Path.cwd().parent / "media" / "twitter")

    async def handle(self, message: Message, url: str):
        user_id = message.from_user.id
        user_sessions[user_id] = {"url": url}

        try:
            status = await message.answer(_("twitter_loading"))

            result = await self.controller.download_media(url)

            if not result["success"] or not result["downloaded_files"]:
                await message.answer(result["message"])
                return

            video = next(
                (f for f in result["downloaded_files"] if f["type"] == "video"), None
            )
            if not video:
                await message.answer(_("twitter_no_files"))
                return

            video_path = Path(video["path"])
            if not video_path.exists():
                await message.answer(_("twitter_no_files"))
                return

            user_sessions[user_id]["video_path"] = str(video_path)

            await status.delete()
            await message.answer_video(
                FSInputFile(video_path),
                caption=_("twitter_video_ready"),
                reply_markup=get_music_download_button("twitter"),
                supports_streaming=True,
            )

            await atomic_clear(video_path)

        except Exception as e:
            logger.exception("TwitterHandler error")
            await message.answer(_("twitter_error") + f"\n{e}")

    def get_sessions(self):
        return user_sessions

    def pop_session(self, user_id: int):
        user_sessions.pop(user_id, None)
