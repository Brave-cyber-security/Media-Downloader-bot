from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _


def get_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("activate_subscription_btn"),
                    callback_data="activate_subscription",
                ),
                InlineKeyboardButton(
                    text=_("invite_friends_btn"), callback_data="invite_friends"
                ),
            ]
        ]
    )


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("confirm_btn"), callback_data="confirm_payment"
                ),
                InlineKeyboardButton(
                    text=_("cancel_btn"), callback_data="cancel_payment"
                ),
            ]
        ]
    )
