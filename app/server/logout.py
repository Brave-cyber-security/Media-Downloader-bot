import asyncio

from aiogram import Bot


async def log_out(bot: Bot, sleep_time: int = 5) -> None:
    """Gracefully close the bot instance."""
    await asyncio.sleep(sleep_time)
    try:
        await bot.close()
    except Exception as e:
        print(f"Error during bot logout: {e}")
