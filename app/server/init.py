import logging
import os
from pathlib import Path
from sqlalchemy.future import select

from app.bot.models import AdminRequirements
from app.core.extensions.utils import WORKDIR
from app.core.databases.postgres import get_general_session


async def admin_init():
    async with get_general_session() as session:
        result = await session.execute(select(AdminRequirements))
        count = len(result.scalars().all())
        if count > 0:
            logging.info("Admin requirements already initialized.")
            return
    async with get_general_session() as session:
        admin_requirements = AdminRequirements(
            referral_count_for_free_month=10,
            premium_price=5000.0,
        )
        session.add(admin_requirements)
        try:
            await session.commit()
        except Exception as e:
            logging.error(f"Error initializing admin requirements: {e}")
            await session.rollback()


def init():
    Path("logs/info").mkdir(parents=True, exist_ok=True)
    Path("logs/warnings").mkdir(parents=True, exist_ok=True)
    Path("logs/errors").mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/info/info.log", mode="a"),
            logging.FileHandler("logs/warnings/warnings.log", mode="a"),
            logging.FileHandler("logs/errors/errors.log", mode="a"),
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("Logger is set up and running.")
    os.makedirs(WORKDIR.parent / "media", exist_ok=True)
    os.makedirs(WORKDIR.parent / "media" / "instagram", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "tiktok", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "snapchat", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "threads", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "likee", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "youtube_shorts", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "twitter", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "media" / "xlsx", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "static" / "pinterest", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "static" / "threads", exist_ok=True)  # done
    os.makedirs(WORKDIR.parent / "static" / "cookie" / "instagram", exist_ok=True)
    os.makedirs(WORKDIR.parent / "static" / "cookie" / "youtube", exist_ok=True)
    os.makedirs(WORKDIR.parent / "static" / "cookie" / "tiktok", exist_ok=True)


from aiogram import Bot
from aiogram.types import BotCommand


async def set_default_commands(bot: Bot):
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start bot"),
            BotCommand(command="lang", description="Change language"),
            BotCommand(command="payment", description="Fill balance"),
            BotCommand(command="balance", description="Check balance"),
            BotCommand(command="top", description="Top 10 music in the world"),
            BotCommand(command="new", description="Top 10 new music in the world"),
            BotCommand(command="help", description="Get help"),
        ]
    )
