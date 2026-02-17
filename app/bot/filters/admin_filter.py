from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from app.core.settings.config import get_settings, Settings

settings: Settings = get_settings()


class AdminFilter(BaseFilter):
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if hasattr(obj, "from_user"):
            return obj.from_user.id in settings.admins_list
        return False
