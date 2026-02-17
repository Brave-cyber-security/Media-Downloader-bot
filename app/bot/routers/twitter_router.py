import time
import re
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.i18n import gettext as _

from app.bot.controller.twitter_controller import TwitterController
from app.bot.handlers import shazam_handler as shz
from app.bot.handlers.twitter_handler import TwitterHandler
from app.bot.handlers.user_handlers import remove_token
from app.bot.keyboards.payment_keyboard import get_payment_keyboard
from app.core.utils.audio import extract_audio_from_video
from app.bot.extensions.clear import atomic_clear
from app.bot.routers.music_router import (
    get_controller,
    format_page_text,
    create_keyboard,
    _cache,
)
from app.bot.keyboards.general_buttons import get_music_download_button
from app.bot.handlers.statistics_handler import update_statistics

logger = logging.getLogger(__name__)
twitter_router = Router()
controller = TwitterController(Path.cwd().parent / "media" / "twitter")
twitter_handler = TwitterHandler()


def extract_twitter_url(text: str) -> str:
    match = re.search(r"https?://(?:www\.)?(twitter|x)\.com/\S+", text)
    return match.group(0) if match else ""


@twitter_router.message(F.text.contains("twitter.com") | F.text.contains("x.com"))
async def handle_twitter_message(message: Message):
    res = await remove_token(message)
    if not res:
        await message.answer(
            _(
                "No requests left. Please top up your balance or invite friends."
            ),
            reply_markup=get_payment_keyboard(),
        )
        return

    await message.answer(_("twitter_detected"))

    user_id = message.from_user.id
    url = extract_twitter_url(message.text)
    if not url:
        await message.answer(_("twitter_invalid_url"))
        return

    twitter_handler.get_sessions()[user_id] = {"url": url}

    try:
        result = await controller.download_media(url)

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

        twitter_handler.get_sessions()[user_id]["video_path"] = str(video_path)

        await message.answer_video(
            FSInputFile(video_path),
            caption=_("twitter_video_ready"),
            reply_markup=get_music_download_button("twitter"),
        )

        await atomic_clear(video_path)

    except Exception as e:
        logger.exception("Twitter download error")
        await message.answer(_("twitter_error") + f"\n{e}")
    await update_statistics(user_id, field="from_twitter")


@twitter_router.callback_query(F.data == "twitter:download_music")
async def handle_twitter_callback(callback_query: CallbackQuery):
    await callback_query.answer(_("extracting"))
    user_id = callback_query.from_user.id

    session = twitter_handler.get_sessions().get(user_id)
    if not session or not session.get("video_path"):
        await callback_query.message.answer(_("session_expired"))
        return

    try:
        audio_path = extract_audio_from_video(session["video_path"])
        if not audio_path:
            await callback_query.message.answer(_("extract_failed"))
            return

        shazam_hits = await shz.recognise_music_from_audio(audio_path)
        if not shazam_hits:
            await callback_query.message.answer(_("music_not_recognized"))
            return

        track = shazam_hits[0]["track"]
        title, artist = track["title"], track["subtitle"]
        search_query = f"{title} {artist}"

        youtube_hits = await get_controller().search(search_query)
        if not youtube_hits:
            youtube_hits = [
                get_controller().ytdict_to_info(
                    {
                        "title": title,
                        "artist": artist,
                        "duration": 0,
                        "id": track.get("key", ""),
                    }
                )
            ]

        await callback_query.message.answer(
            _("music_found").format(title=title, artist=artist), parse_mode="HTML"
        )

        _cache[user_id] = {
            "hits": youtube_hits,
            "timestamp": time.time(),
        }

        await callback_query.message.answer(
            format_page_text(youtube_hits, 0),
            reply_markup=create_keyboard(user_id, 0, add_video=True),
            parse_mode="HTML",
        )

        await atomic_clear(audio_path)

    except Exception as e:
        logger.exception("Shazam error")
        await callback_query.message.answer(_("recognition_error") + f": {str(e)}")

    finally:
        twitter_handler.pop_session(user_id)
