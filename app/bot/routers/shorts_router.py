import asyncio
import logging
import re
import time

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.i18n import gettext as _

from app.bot.controller.shorts_controller import YouTubeShortsController
from app.bot.extensions.clear import atomic_clear
from app.bot.handlers.statistics_handler import update_statistics
from app.bot.handlers.user_handlers import remove_token
from app.bot.keyboards.general_buttons import get_music_download_button
from app.bot.keyboards.payment_keyboard import get_payment_keyboard
from app.bot.routers.music_router import (
    _cache,
    create_keyboard,
    format_page_text,
    get_controller,
)
from app.bot.state.session_store import user_sessions
from app.core.extensions.utils import WORKDIR
from app.core.utils.audio import extract_audio_from_video

shorts_router = Router()
logger = logging.getLogger(__name__)


def extract_shorts_url(text: str) -> str:
    """Extract YouTube Shorts URL from text."""
    patterns = [
        r"https?://(?:www\.)?youtube\.com/shorts/[^\s]+",
        r"https?://youtu\.be/[^\s]+",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


@shorts_router.message(
    F.text.contains("youtube.com/shorts") | F.text.contains("youtu.be")
)
async def handle_shorts_link(message: Message):
    res = await remove_token(message)
    if not res:
        await message.answer(
            _("No requests left. Please top up your balance or invite friends."),
            reply_markup=get_payment_keyboard(),
        )
        return

    url = extract_shorts_url(message.text)
    if not url:
        await message.answer(_("invalid_url"))
        return

    progress_message = await message.answer(_("shorts_loading"))

    user_id = message.from_user.id
    user_sessions[user_id] = {"url": url}

    controller = YouTubeShortsController(WORKDIR.parent / "media" / "youtube_shorts")
    try:
        video_path = await asyncio.wait_for(controller.download_video(url), timeout=75)
        if not video_path:
            await message.answer(_("shorts_no_files"))
            return

        user_sessions[user_id]["video_path"] = video_path

        await message.answer_video(
            FSInputFile(video_path),
            caption=_("shorts_video_ready"),
            reply_markup=get_music_download_button("shorts"),
            supports_streaming=True,
        )

        await update_statistics(user_id, field="from_shorts")

    except Exception as e:
        error_text = str(e).lower()
        if (
            "not available on this app" in error_text
            or "botdetection" in error_text
            or "sign in to confirm" in error_text
            or "requested format is not available" in error_text
        ):
            logger.warning("Shorts blocked by YouTube restrictions: %s", e)
            await message.answer(
                "YouTube cheklovi sababli bu Shorts yuklab bo'lmadi. "
                "Iltimos, boshqa Shorts link yuboring."
            )
        elif isinstance(e, asyncio.TimeoutError):
            logger.warning("Shorts download timeout: %s", e)
            await message.answer("Download timed out. Please try again.")
        else:
            logger.exception("Shorts download error")
            await message.answer(_("shorts_error"))
    finally:
        try:
            await progress_message.delete()
        except Exception:
            pass


@shorts_router.callback_query(F.data == "shorts:download_music")
async def handle_shorts_music(callback_query: CallbackQuery):
    await callback_query.answer(_("extracting"))

    from app.bot.handlers import shazam_handler as shz

    user_id = callback_query.from_user.id
    session = user_sessions.get(user_id)

    if not session or not session.get("video_path"):
        await callback_query.message.answer(_("session_expired"))
        return

    try:
        video_path = session["video_path"]
        audio_path = extract_audio_from_video(video_path)

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
        logger.exception("Shorts Shazam xatolik:")
        await callback_query.message.answer(_("recognition_error") + f": {str(e)}")

    user_sessions.pop(user_id, None)
