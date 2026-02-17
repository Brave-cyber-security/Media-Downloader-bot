from sqlalchemy.future import select
from sqlalchemy import func

from app.bot.models import Statistics
from app.core.databases.postgres import get_general_session


async def get_statistics_by_tg_id(tg_id: int) -> Statistics | None:
    async with get_general_session() as session:
        query = select(Statistics).where(Statistics.tg_id == tg_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def create_statistics(
    tg_id: int,
) -> Statistics:
    statistics = Statistics(
        tg_id=tg_id,
    )
    exists = await get_statistics_by_tg_id(tg_id)
    if exists:
        return exists
    async with get_general_session() as session:
        session.add(statistics)
        await session.commit()
        return statistics


async def update_statistics(tg_id: int, field: str) -> Statistics:
    """
    Fields:
    - user_id: ID of the user
    - from_text: Count of text messages sent by the user
    - from_voice: Count of voice messages sent by the user
    - from_youtube: Count of YouTube links shared by the user
    - from_tiktok: Count of TikTok links shared by the user
    - from_like: Count of likes given by the user
    - from_snapchat: Count of Snapchat links shared by the user
    - from_instagram: Count of Instagram links shared by the user
    - from_twitter: Count of Twitter links shared by the user
    - from_video: Count of videos shared by the user
    """
    async with get_general_session() as session:
        query = select(Statistics).where(Statistics.tg_id == tg_id)
        result = await session.execute(query)
        statistics = result.scalar_one_or_none()
        if not statistics:
            statistics = Statistics(tg_id=tg_id)
            session.add(statistics)
            await session.flush()
        statistics.add_one(field)
        await session.commit()
        return statistics


async def get_all_statistics() -> dict[str, int]:
    async with get_general_session() as session:
        query = select(
            func.coalesce(func.sum(Statistics.from_text), 0).label("from_text"),
            func.coalesce(func.sum(Statistics.from_voice), 0).label("from_voice"),
            func.coalesce(func.sum(Statistics.from_youtube), 0).label("from_youtube"),
            func.coalesce(func.sum(Statistics.from_tiktok), 0).label("from_tiktok"),
            func.coalesce(func.sum(Statistics.from_like), 0).label("from_like"),
            func.coalesce(func.sum(Statistics.from_snapchat), 0).label("from_snapchat"),
            func.coalesce(func.sum(Statistics.from_instagram), 0).label(
                "from_instagram"
            ),
            func.coalesce(func.sum(Statistics.from_twitter), 0).label("from_twitter"),
        )

        result = await session.execute(query)
        row = result.one_or_none()

        return {
            "from_text": row.from_text,
            "from_voice": row.from_voice,
            "from_youtube": row.from_youtube,
            "from_tiktok": row.from_tiktok,
            "from_like": row.from_like,
            "from_snapchat": row.from_snapchat,
            "from_instagram": row.from_instagram,
            "from_twitter": row.from_twitter,
        }
