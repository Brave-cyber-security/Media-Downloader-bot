import time
import re
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.utils.i18n import gettext as _

from app.bot.handlers.user_handlers import remove_token
from app.bot.keyboards.payment_keyboard import get_payment_keyboard
from app.core.utils.audio import extract_audio_from_video
from app.bot.controller.threads_controller import ThreadsController
from app.bot.handlers import shazam_handler as shz
from app.bot.routers.music_router import (
    get_controller,
    format_page_text,
    create_keyboard,
    _cache,
)
from app.bot.keyboards.general_buttons import get_music_download_button
from app.bot.handlers.statistics_handler import update_statistics
from app.bot.extensions.clear import atomic_clear

threads_router = Router()
logger = logging.getLogger(__name__)
user_sessions = {}


# URL ajratish
def extract_threads_url(text: str) -> str:
    patterns = [
        r"https?://(?:www\.)?threads\.com/[@\w\.-]+/post/[\w\.-]+",
        r"https?://(?:www\.)?threads\.com/t/[\w\.-]+",
        r"https?://(?:www\.)?threads\.com/[\w\.-]+/[\w\.-]+",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


@threads_router.message(F.text.contains("threads.com"))
async def handle_threads_link(message: Message):
    res = await remove_token(message)
    if not res:
        await message.answer(
            _(
                "No requests left. Please top up your balance or invite friends."
            ),
            reply_markup=get_payment_keyboard(),
        )
        return
    url = extract_threads_url(message.text)
    if not url:
        await message.answer(_("threads_invalid_url"))
        return

    await message.answer(_("threads_loading"))

    user_id = message.from_user.id
    user_sessions[user_id] = {"url": url}

    controller = ThreadsController(Path.cwd().parent / "media" / "threads")
    try:
        result = await controller.download_media(url)
        if not result["success"]:
            await message.answer(result["message"])
            return

        files = result["downloaded_files"]
        if not files:
            await message.answer(_("threads_no_files"))
            return

        video_file = next((f for f in files if f["type"] == "video"), None)
        if not video_file:
            await message.answer(_("threads_no_files"))
            return

        video_path = Path(video_file["path"])
        if not video_path.exists():
            await message.answer(_("threads_no_files"))
            return

        user_sessions[user_id]["video_path"] = str(video_path)

        await message.answer_video(
            FSInputFile(video_path),
            caption=_("threads_video_ready"),
            reply_markup=get_music_download_button("threads"),
        )

    except Exception as e:
        logger.exception("Threads download error")
        await message.answer(_("threads_error") + f"\n{e}")
    finally:
        controller.close()
        await update_statistics(user_id, field="from_threads")


@threads_router.callback_query(F.data == "threads:download_music")
async def handle_threads_callback(callback_query: CallbackQuery):
    await callback_query.answer(_("extracting"))

    user_id = callback_query.from_user.id
    session = user_sessions.get(user_id)
    if not session or not session.get("video_path"):
        await callback_query.message.answer(_("session_expired"))
        return

    try:
        video_path = session["video_path"]
        audio_path = extract_audio_from_video(
            video_path
        )  # Use same smart extract method

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
        logger.exception("Threads music recognition error")
        await callback_query.message.answer(_("recognition_error") + f": {str(e)}")

    user_sessions.pop(user_id, None)
