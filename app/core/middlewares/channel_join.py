from typing import Callable, Awaitable, Dict, Any, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from app.bot.handlers.channel_handler import fetch_unsubscribed_channels
from app.bot.handlers.referral_handler import is_free_for_month
from app.bot.keyboards.channels_keyboards import get_channel_keyboard


class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        bot = data["bot"]
        user_id = event.from_user.id
        # if isinstance(event, CallbackQuery):
        #     print(event.data)
        #     unsubscribed = await fetch_unsubscribed_channels(user_id, bot)
        #     if unsubscribed:
        #         buttons: InlineKeyboardMarkup = await get_channel_keyboard(unsubscribed)
        #         await event.answer(
        #             "🚫 You still need to join these channels.", show_alert=True
        #         )
        #         await event.message.edit_reply_markup(reply_markup=buttons)
        #         return None
        #
        #     await event.answer("✅ Thank you for subscribing!", show_alert=True)
        #     await event.message.delete_reply_markup()
        #     return None

        if isinstance(event, Message):
            if await is_free_for_month(user_id):
                return await handler(event, data)
            text = event.text or ""
            if (
                text.startswith("/start")
                or text.startswith("/lang")
                or text.startswith("/help")
                or text.startswith("/top")
                or text.startswith("/new")
                or text.startswith("/payment")
                or text.startswith("/balance")
                or text.startswith("/developer")
            ):
                return await handler(event, data)
            unsubscribed = await fetch_unsubscribed_channels(user_id, bot)
            if unsubscribed:
                buttons = await get_channel_keyboard(unsubscribed)
                prompt = f"📢 Please subscribe to the following {len(unsubscribed)} channels first:"
                try:
                    await event.answer(text=prompt, reply_markup=buttons)
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
                return None

        return await handler(event, data)
