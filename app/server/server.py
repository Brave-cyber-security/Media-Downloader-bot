import asyncio, logging, sys

from aiogram import Bot, Dispatcher
from aiogram.utils.i18n import I18n
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.telegram import TelegramAPIServer

from app.bot.routers import v1_router
from app.core.middlewares.language_middleware import UserI18nMiddleware
from app.core.settings.config import get_settings, Settings
from app.core.extensions.utils import WORKDIR
from app.core.middlewares.channel_join import CheckSubscriptionMiddleware
from app.core.middlewares.group_chat_middle import GroupChatMiddleware
from app.server.init import init, admin_init, set_default_commands
from app.server.logout import log_out

settings: Settings = get_settings()
i18n = I18n(path=WORKDIR / "locales", default_locale="uz", domain="messages")


async def main() -> None:
    if settings.USE_LOCAL_BOT_API:
        bot = Bot(token=settings.BOT_TOKEN)
        await log_out(bot, 10)
        local_server = TelegramAPIServer.from_base(settings.LOCAL_BOT_API_URL)
        bot = Bot(token=settings.BOT_TOKEN, server=local_server)
    else:
        bot = Bot(token=settings.BOT_TOKEN)

    init()
    await bot.delete_webhook(drop_pending_updates=True)

    i18n_middleware = UserI18nMiddleware(i18n)
    dp = Dispatcher(storage=MemoryStorage())
    dp.bot = bot

    # Group chat middleware
    dp.message.middleware(GroupChatMiddleware())
    dp.callback_query.middleware(GroupChatMiddleware())

    # I18n middleware
    dp.message.middleware(i18n_middleware)
    dp.callback_query.middleware(i18n_middleware)

    # Subscription middleware
    dp.message.middleware(CheckSubscriptionMiddleware())
    dp.callback_query.middleware(CheckSubscriptionMiddleware())

    # Routerlarni qo'shish
    dp.include_router(v1_router)

    await set_default_commands(bot)
    await admin_init()
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
