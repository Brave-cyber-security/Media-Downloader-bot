import asyncio
from aiogram.types import ContentType
from aiogram import Bot
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app.bot.models import User
from app.bot.keyboards.admin_keyboards import get_admin_panel_keyboard
from app.bot.models import AdminRequirements
from app.core.databases.postgres import get_general_session
from sqlalchemy.future import select
from app.core.settings.config import get_settings, Settings

settings: Settings = get_settings()


async def get_token_per_referral() -> int:
    async with get_general_session() as session:
        query = select(AdminRequirements)
        result = await session.execute(query)
        return result.scalars().first().referral_count_for_free_month


async def update_token_per_referral(new_value: int) -> None:
    async with get_general_session() as session:
        query = select(AdminRequirements)
        result = await session.execute(query)
        admin_req = result.scalars().first()
        if admin_req:
            admin_req.referral_count_for_free_month = new_value
            session.add(admin_req)
            await session.commit()
        else:
            raise ValueError("AdminRequirements not found in the database.")


async def get_premium_price() -> int:
    async with get_general_session() as session:
        query = select(AdminRequirements)
        result = await session.execute(query)
        return result.scalars().first().premium_price


async def update_premium_price(new_value: float) -> None:
    async with get_general_session() as session:
        query = select(AdminRequirements)
        result = await session.execute(query)
        admin_req = result.scalars().first()
        if admin_req:
            admin_req.premium_price = new_value
            session.add(admin_req)
            await session.commit()
        else:
            raise ValueError("AdminRequirements not found in the database.")


async def get_last_7_days_statistics() -> dict:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    year_start = now - timedelta(days=365)

    async with get_general_session() as session:

        def count_where(*conds):
            q = (
                select(func.count()).select_from(User).where(*conds)
                if conds
                else select(func.count()).select_from(User)
            )
            return session.execute(q)

        today_res = await count_where(User.created_at >= today_start)
        yesterday_res = await count_where(
            User.created_at >= yesterday_start, User.created_at < today_start
        )
        week_res = await count_where(User.created_at >= week_start)
        month_res = await count_where(User.created_at >= month_start)
        year_res = await count_where(User.created_at >= year_start)
        all_res = await count_where()

        today = today_res.scalar_one()
        yesterday = yesterday_res.scalar_one()
        last_week = week_res.scalar_one()
        last_month = month_res.scalar_one()
        last_year = year_res.scalar_one()
        all_time = all_res.scalar_one()

        ref_q = (
            select(User.referred_by, func.count(User.id).label("ref_count"))
            .where(User.referred_by != None)
            .group_by(User.referred_by)
            .order_by(desc("ref_count"))
            .limit(10)
        )
        ref_rows = (await session.execute(ref_q)).all()
        ref_ids = [row[0] for row in ref_rows]

        # fetch names in one go
        if ref_ids:
            users_q = select(User.tg_id, User.first_name, User.last_name).where(
                User.tg_id.in_(ref_ids)
            )
            users = (await session.execute(users_q)).all()
            name_map = {tg: f"{fn} {ln or ''}".strip() for tg, fn, ln in users}
        else:
            name_map = {}

        top_referrers = [
            {"tg_id": tg, "name": name_map.get(tg, str(tg)), "count": cnt}
            for tg, cnt in ref_rows
        ]

    return {
        "today": today,
        "yesterday": yesterday,
        "last_week": last_week,
        "last_month": last_month,
        "last_year": last_year,
        "all_time": all_time,
        "top_referrers": top_referrers,
    }


bot = Bot(settings.BOT_TOKEN)


async def run_broadcast(text: str, media: tuple[str, str] | None, admin_id: int):
    await asyncio.sleep(1)  # allow handler to return
    batch = 1000

    async with get_general_session() as session:
        total = (await session.execute(select(User))).scalars().all()
        total_count = len(total)

    for offset in range(0, total_count, batch):
        async with get_general_session() as session:
            uids = (
                (await session.execute(select(User.tg_id).offset(offset).limit(batch)))
                .scalars()
                .all()
            )

        for uid in uids:
            try:
                if media:
                    ctype, fid = media
                    if ctype == ContentType.PHOTO:
                        await bot.send_photo(
                            uid, photo=fid, caption=text, parse_mode="HTML"
                        )
                    elif ctype == ContentType.VIDEO:
                        await bot.send_video(
                            uid, video=fid, caption=text, parse_mode="HTML"
                        )
                    else:
                        await bot.send_document(
                            uid, document=fid, caption=text, parse_mode="HTML"
                        )
                else:
                    await bot.send_message(uid, text, parse_mode="HTML")
            except:
                pass
            await asyncio.sleep(0.05)

    await bot.send_message(
        admin_id, "📬 Broadcast complete!", reply_markup=get_admin_panel_keyboard()
    )
