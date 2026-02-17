from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable, Union
import logging

logger = logging.getLogger(__name__)


class GroupChatMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Universal middleware for all event types"""

        # Message yoki CallbackQuery bo'lsa chat info qo'shish
        chat = None

        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        if chat:
            chat_type = chat.type

            # Chat type bo'yicha data qo'shish
            data["chat_type"] = chat_type
            data["chat_id"] = chat.id

            if chat_type in ["group", "supergroup"]:
                data["is_group"] = True
                data["group_id"] = chat.id

                # Guruh haqida qo'shimcha ma'lumot
                data["group_title"] = getattr(chat, "title", "Unknown")
                data["member_count"] = getattr(chat, "member_count", 0)

                logger.debug(f"Group message detected: {chat.title} ({chat.id})")
            else:
                data["is_group"] = False
                data["is_private"] = chat_type == "private"

                logger.debug(f"Private message detected: {chat.id}")

        return await handler(event, data)
