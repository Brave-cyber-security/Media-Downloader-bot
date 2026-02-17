from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.utils.i18n import gettext as _

from app.bot.extensions.clear import atomic_clear
from app.bot.handlers.instagram_handler import (
    download_instagram_video_only_mp4,
    validate_instagram_url,
    extract_audio_from_instagram_video,
)
from app.bot.handlers.statistics_handler import update_statistics
from app.bot.handlers.user_handlers import remove_token
from app.bot.keyboards.general_buttons import get_music_download_button
from app.bot.keyboards.payment_keyboard import get_payment_keyboard
from app.bot.routers.music_router import (
    format_page_text,
    create_keyboard,
    get_controller,
    _cache,
)
from app.core.settings.config import get_settings, Settings
from app.bot.handlers import shazam_handler as shz

settings: Settings = get_settings()

instagram_router = Router()
user_sessions = {}  # Session storage

import time


@instagram_router.message(F.text.contains("instagram.com"))
async def handle_instagram_link(message: Message):
    res = await remove_token(message)
    if not res:
        await message.answer(
            _(
                "No requests left. Please top up your balance or invite friends."
            ),
            reply_markup=get_payment_keyboard(),
        )
        return
    await message.answer(_("ig_detected"))

    user_id = message.from_user.id
    instagram_url = validate_instagram_url(message.text)

    user_sessions[user_id] = {"url": instagram_url}
    video_path = await download_instagram_video_only_mp4(instagram_url)
    user_sessions[user_id]["video_path"] = video_path

    await message.answer_video(
        FSInputFile(video_path),
        caption=_("ig_video_ready"),
        reply_markup=get_music_download_button("instagram"),
    )
    await update_statistics(message.from_user.id, field="from_instagram")


@instagram_router.callback_query(F.data.startswith("instagram:"))
async def handle_instagram_callback(callback_query: CallbackQuery):
    action = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id

    if action != "download_music":
        await callback_query.answer(_("ig_unknown_action"))
        return

    await callback_query.answer(_("ig_extracting"))

    session = user_sessions.get(user_id)
    if not session or not session.get("url"):
        await callback_query.message.answer(_("ig_session_expired"))
        return

    try:
        audio_path = await extract_audio_from_instagram_video(session["url"])
        if not audio_path:
            await callback_query.message.answer(_("ig_extract_failed"))
            return

        shazam_hits = await shz.recognise_music_from_audio(audio_path)
        if not shazam_hits:
            await callback_query.message.answer(_("ig_music_not_recognized"))
            return

        track = shazam_hits[0]["track"]
        title = track["title"]
        artist = track["subtitle"]
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
            _("ig_music_found").format(title=title, artist=artist),
            parse_mode="HTML",
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
        print(f"Error during recognition: {str(e)}")
        await callback_query.message.answer(_("ig_recognition_error"))

    user_sessions.pop(user_id, None)
