import asyncio
import logging

from aiogram import Bot

logger = logging.getLogger(__name__)


async def log_out(bot: Bot, sleep_time: int = 5) -> None:
    """Gracefully close the bot instance."""
    await asyncio.sleep(sleep_time)
    try:
        await bot.close()
    except Exception as e:
        message = str(e).lower()
        if "too many requests" in message or "flood control" in message:
            logger.warning("Skipping bot.close() because flood control is active.")
            return
        logger.warning(f"bot.close() failed: {e}")
