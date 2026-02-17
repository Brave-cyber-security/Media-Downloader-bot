from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
from aiogram import types

from app.bot.handlers.user_handlers import get_user_by_tg_id
from app.bot.models import User


class UserI18nMiddleware(SimpleI18nMiddleware):
    def __init__(self, i18n: I18n):
        super().__init__(i18n)

    async def get_locale(self, event: types.TelegramObject, data: dict) -> str:
        user = data.get("event_from_user")

        if user and user.id:
            try:
                db_user: User = await get_user_by_tg_id(user.id)
                if db_user and db_user.language_code:
                    return db_user.language_code
            except Exception as e:
                print(f"Error getting user language: {e}")
        if user and user.language_code:
            return user.language_code
        return self.i18n.default_locale
