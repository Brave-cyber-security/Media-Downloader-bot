from aiogram import Router

admin_router = Router()

from app.bot.routers.admin_router.settings_router import settings_router
from app.bot.routers.admin_router.channel_crud import channel_router
from app.bot.routers.admin_router.main_menu import main_menu_router
from app.bot.routers.admin_router.payment_router import router as payment_router

admin_router.include_routers(
    settings_router, channel_router, main_menu_router, payment_router
)

__all__ = ("admin_router",)
