from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.i18n import gettext as _
from app.bot.handlers.channel_handler import get_all_channels
from app.bot.models import Channel



async def channels_list_keyboard() -> InlineKeyboardMarkup:
    channels: list[Channel] = await get_all_channels()

    inline_keyboard = [
        row
        for ch in channels
        for row in (
            [
                InlineKeyboardButton(
                    text=f"📺 {ch.name}", callback_data=f"channel:info:{ch.id}"
                ),
                InlineKeyboardButton(text=_("view_link_btn"), url=ch.link),
            ],
            [
                InlineKeyboardButton(
                    text="✅" if ch.is_active else "❌",
                    callback_data=f"channel:toggle:{ch.id}",
                ),
                InlineKeyboardButton(
                    text=_("update_btn"), callback_data=f"channel:update:{ch.id}"
                ),
                InlineKeyboardButton(
                    text=_("delete_btn"), callback_data=f"channel:delete:{ch.id}"
                ),
            ],
        )
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_("yes_btn"), callback_data="channel_active:yes"),
                InlineKeyboardButton(text=_("no_btn"), callback_data="channel_active:no"),
            ]
        ]
    )


def skip_kb(label: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def get_channel_keyboard(not_joined: list[Channel]):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📢 {ch.name}", url=ch.link)]
            for ch in not_joined
        ]
        + [
            [
                InlineKeyboardButton(
                    text=_("check_subscription_btn"), callback_data="check_subscription"
                )
            ]
        ]
    )
