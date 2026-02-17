from app.bot.models import Channel
from app.core.databases.postgres import get_general_session
from sqlalchemy.future import select
from aiogram.exceptions import TelegramBadRequest


async def get_channel_by_id(channel_id: int) -> Channel | None:
    async with get_general_session() as session:
        query = select(Channel).where(Channel.id == channel_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def get_all_channels(is_active: bool | None = None) -> list[Channel]:
    async with get_general_session() as session:
        query = select(Channel)
        if is_active is not None:
            query = query.where(Channel.is_active == is_active)
        result = await session.execute(query.order_by(Channel.name))
        return result.scalars().all()


async def add_channel(
    name: str, link: str | None, channel_id: int | None, is_active: bool = True
) -> Channel:
    if not name and not link:
        raise ValueError("Either name or link must be provided for the channel.")
    async with get_general_session() as session:
        channel = Channel(
            name=name, link=link, channel_id=channel_id, is_active=is_active
        )
        session.add(channel)
        await session.commit()
        return channel


async def update_channel(
    channel_id: int,
    /,
    *,
    name: str | None = None,
    link: str | None = None,
    is_active: bool | None = None,
) -> Channel:
    async with get_general_session() as session:
        channel = await get_channel_by_id(channel_id)
        if not channel:
            raise ValueError("Channel not found.")
        channel.update(name=name, link=link, is_active=is_active)
        session.add(channel)
        await session.commit()
        return channel


async def delete_channel(channel_id: int) -> None:
    async with get_general_session() as session:
        channel = await get_channel_by_id(channel_id)
        if not channel:
            raise ValueError("Channel not found.")
        await session.delete(channel)
        await session.commit()


async def fetch_unsubscribed_channels(user_id: int, bot) -> list[Channel]:
    unsubscribed: list[Channel] = []
    channels = await get_all_channels(is_active=True)

    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=channel.channel_id, user_id=user_id
            )
            if member.status not in ("member", "administrator", "creator"):
                unsubscribed.append(channel)
        except TelegramBadRequest:
            continue

    return unsubscribed
