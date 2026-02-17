from sqlalchemy.future import select
from datetime import datetime, timedelta

from app.bot.models import Referral, AdminRequirements, User
from app.core.databases.postgres import get_general_session


async def get_referral_by_tg_id(
    tg_id: int, last_month: bool | None = None
) -> list[Referral]:
    async with get_general_session() as session:
        query = select(Referral).where(Referral.tg_id == tg_id)
        if last_month:
            query = query.where(
                Referral.created_at >= datetime.now() - timedelta(days=30)
            )
        result = await session.execute(query)
        return result.scalars().all()


async def add_referral(tg_id: int, invited_tg_id: int) -> Referral | None:
    if tg_id == invited_tg_id:
        return None
    async with get_general_session() as session:
        result = await session.execute(select(Referral).where(Referral.tg_id == tg_id))
        if result.scalar_one_or_none() is not None:
            return None
        referral = Referral(tg_id=tg_id, invited_tg_id=invited_tg_id)
        session.add(referral)
        await session.commit()
        return referral


async def get_user_by_tg_id(tg_id: int) -> User | None:
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()


async def is_free_for_month(tg_id: int) -> bool:
    user = await get_user_by_tg_id(tg_id)
    if not user:
        return False
    async with get_general_session() as session:
        result = await session.execute(select(AdminRequirements))
        admin_req = result.scalars().first()
        if not admin_req:
            return True
        referral_count = await session.execute(
            select(Referral).where(Referral.tg_id == tg_id)
        )
        count = len(referral_count.scalars().all())
        return count >= admin_req.referral_count_for_free_month or user.is_premium()
