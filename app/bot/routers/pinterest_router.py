import time
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.utils.i18n import gettext as _

from app.bot.extensions.clear import atomic_clear
from app.bot.handlers.statistics_handler import update_statistics
from app.bot.handlers.pinterest_handler import download_pinterest_media
from app.bot.handlers import shazam_handler as shz
from app.bot.handlers.user_handlers import remove_token
from app.bot.keyboards.payment_keyboard import get_payment_keyboard
from app.bot.routers.music_router import (
    get_controller,
    format_page_text,
    create_keyboard,
    _cache,
)
from app.bot.keyboards.general_buttons import get_music_download_button
from app.core.settings.config import get_settings, Settings
from pathlib import Path
import logging
import moviepy

settings: Settings = get_settings()
pinterest_router = Router()
logger = logging.getLogger(__name__)
user_sessions = {}


def extract_audio_from_video(video_path: str) -> str | None:
    try:
        audio_path = str(Path(video_path).with_suffix(".mp3"))
        clip = moviepy.VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()
        return audio_path
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return None


@pinterest_router.message(
    F.text.regexp(r"(https?://)?(www\.)?(pin\.it|pinterest\.com)/[^\s]+")
)
async def handle_pinterest_link(message: Message):
    res = await remove_token(message)
    if not res:
        await message.answer(
            _(
                "No requests left. Please top up your balance or invite friends."
            ),
            reply_markup=get_payment_keyboard(),
        )
        return
    await message.answer(_("pinterest_detected"))

    user_id = message.from_user.id
    url = message.text.strip()
    user_sessions[user_id] = {"url": url}

    try:
        result = await download_pinterest_media(url)
        if not result:
            await message.answer(_("pinterest_download_failed"))
            return

        file_path, media_type = result
        user_sessions[user_id]["video_path"] = file_path

        if media_type == "video":
            await message.answer_video(
                FSInputFile(file_path),
                caption=_("pinterest_video_ready"),
                reply_markup=get_music_download_button("pinterest"),
                supports_streaming=True,
            )
        elif media_type == "image":
            await message.answer_photo(FSInputFile(file_path))
        else:
            await message.answer_document(FSInputFile(file_path))

        await update_statistics(user_id, field="from_pinterest")

    except Exception as e:
        logger.error(f"Pinterest error: {e}")
        await message.answer(_("pinterest_download_error"))


@pinterest_router.callback_query(F.data.startswith("pinterest:"))
async def handle_pinterest_callback(callback_query: CallbackQuery):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    if action != "download_music":
        await callback_query.answer(_("unknown_action"))
        return

    await callback_query.answer(_("extracting"))

    session = user_sessions.get(user_id)
    if not session or not session.get("video_path"):
        await callback_query.message.answer(_("session_expired"))
        return

    try:
        audio_path = extract_audio_from_video(session["video_path"])
        if not audio_path or not Path(audio_path).exists():
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
        await callback_query.message.answer(
            _("recognition_error") + f": {str(e)[:100]}"
        )

    user_sessions.pop(user_id, None)
