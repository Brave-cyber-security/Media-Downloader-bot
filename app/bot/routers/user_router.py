from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.utils.i18n import gettext as _
from app.bot.handlers.admin import get_token_per_referral
from app.bot.handlers.referral_handler import get_user_by_tg_id
from app.bot.handlers.user_handlers import get_referral_count
from app.core.settings.config import get_settings, Settings

user_router = Router()
settings: Settings = get_settings()
bot = Bot(settings.BOT_TOKEN)

from urllib.parse import quote_plus


@user_router.message(F.text.contains("Refer Friends and Earn"))
async def handle_refer_friends(message: Message):
    count = await get_referral_count(message.from_user.id)
    token_count = await get_token_per_referral()
    bot_info = await bot.get_me()

    if not bot_info.username:
        await message.answer(_("refer_bot_username_missing"))
        return

    referral_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"

    text = _("refer_message").format(
        count=count, token_count=token_count, referral_link=referral_link
    )

    encoded_url = quote_plus(referral_link)
    encoded_text = quote_plus("🎁 " + _("refer_share_text"))

    share_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("refer_share_btn"),
                    url=f"https://t.me/share/url?url={encoded_url}&text={encoded_text}",
                )
            ]
        ]
    )

    await message.answer(text, parse_mode="HTML", reply_markup=share_button)


@user_router.callback_query(F.data == "invite_friends")
async def invite_friends(callback_query: CallbackQuery):
    user = await get_user_by_tg_id(callback_query.from_user.id)
    bot_username = (await callback_query.bot.get_me()).username

    if not bot_username:
        await callback_query.message.answer(_("refer_bot_username_missing"))
        return

    link = user.get_referral_link(bot_username)
    text = _("refer_message").format(
        count=await get_referral_count(user.tg_id),
        token_count=await get_token_per_referral(),
        referral_link=link,
    )

    # Encode URL for Telegram's share link
    encoded_url = quote_plus(link)
    encoded_text = quote_plus("🎁 " + _("refer_share_text"))

    share_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("refer_share_btn"),
                    url=f"https://t.me/share/url?url={encoded_url}&text={encoded_text}",
                )
            ]
        ]
    )

    await callback_query.message.answer(
        text, parse_mode="HTML", reply_markup=share_button
    )
    await callback_query.answer()

