from sqlalchemy.future import select
from aiogram.types import FSInputFile, Message
from aiogram import Bot
from sqlalchemy.exc import MultipleResultsFound

from app.bot.models import Backup
from app.core.databases.postgres import get_general_session
from app.core.settings.config import get_settings, Settings

settings: Settings = get_settings()
bot = Bot(settings.BOT_TOKEN)


async def get_from_backup(url: str) -> Backup | None:
    async with get_general_session() as session:
        query = select(Backup).where(Backup.url == url)
        result = await session.execute(query)
        return result.scalar_one_or_none()


# async def add_to_backup(url: str, video_path: str) -> None:
#     video = FSInputFile(video_path)
#     sent_msg: Message = await bot.send_video(chat_id=settings.CHANNEL_ID, video=video)
#     async with get_general_session() as session:
#         backup = Backup(url=url, message_id=sent_msg.message_id)
#         session.get_transaction()
#         try:
#             session.add(backup)
#             await session.commit()
#         except MultipleResultsFound:
#             await session.rollback()
#             return
