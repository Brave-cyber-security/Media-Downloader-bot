from aiogram import Router

from app.bot.routers.admin_router import admin_router
from app.bot.routers.music_router import music_router
from app.bot.routers.pinterest_router import pinterest_router
from app.bot.routers.threads_router import threads_router
from app.bot.routers.start_router import start_router
from app.bot.routers.shorts_router import shorts_router
from app.bot.routers.twitter_router import twitter_router
from app.bot.routers.language_router import language_router
from app.bot.routers.instagram_router import instagram_router
from app.bot.routers.tiktok_router import tiktok_router
from app.bot.routers.snapchat_router import snapchat_router
from app.bot.routers.likee_router import likee_router
from app.bot.routers.user_router import user_router
from app.bot.handlers.group_handler import group_router

v1_router = Router()

# MUHIM: Group router birinchi bo'lishi kerak
# Chunki u specific filterlar bilan ishlaydi
v1_router.include_routers(
    group_router,  # 1. Group commands (yuqori prioritet)
    admin_router,  # 2. Admin commands
    start_router,  # 3. Start va umumiy commands
    pinterest_router,  # 4. Platform-specific routers
    snapchat_router,
    language_router,
    shorts_router,
    twitter_router,
    threads_router,
    instagram_router,
    tiktok_router,
    likee_router,
    user_router,
    music_router,  # Oxirgi
)

__all__ = ("v1_router",)
