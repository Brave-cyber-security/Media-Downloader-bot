from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.i18n import gettext as _
from app.core.settings.config import get_settings, Settings

settings: Settings = get_settings()


def get_music_download_button(media_name: str):
    buttons = [
        InlineKeyboardButton(
            text=_("download_music_btn"), callback_data=f"{media_name}:download_music"
        ),
    ]

    return InlineKeyboardMarkup(row_width=2, inline_keyboard=[buttons])


def main_menu_keyboard(message: Message) -> ReplyKeyboardMarkup:
    buttons: list[list[KeyboardButton]] = []

    if message.from_user.id in settings.admins_list:
        buttons.append([KeyboardButton(text="Admin Panel")])

    buttons.extend(
        [
            [KeyboardButton(text="/payment"), KeyboardButton(text="/balance")],
            [KeyboardButton(text="Refer Friends and Earn")],
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Choose an option",
    )
