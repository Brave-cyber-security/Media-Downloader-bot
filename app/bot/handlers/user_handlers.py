from aiogram.types import Message
from datetime import datetime, timedelta

from app.bot.models import User, AdminRequirements
from app.core.databases.postgres import get_general_session
from sqlalchemy.future import select

DEFAULT_FREE_REQUESTS = 10


async def get_user_by_tg_id(tg_id: int) -> User | None:
    async with get_general_session() as session:
        user = await session.execute(select(User).where(User.tg_id == tg_id))
        return user.scalar_one_or_none()


async def update_user_by_tg_id(tg_id, data: dict) -> User:
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(tg_id=tg_id, **data)
            session.add(user)
        else:
            user.update(**data)
        await session.commit()
        return user


async def update_user_by_message(message: Message) -> User:
    data = {
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "username": message.from_user.username,
        "is_tg_premium": (
            message.from_user.is_premium if message.from_user.is_premium else False
        ),
    }
    return await update_user_by_tg_id(message.from_user.id, data)


async def create_user(message: Message, ref_id: int | None = None) -> User:
    async with get_general_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            existing_user.update(
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                username=message.from_user.username,
                is_tg_premium=(
                    message.from_user.is_premium
                    if message.from_user.is_premium
                    else False
                ),
            )
            await session.commit()
            return existing_user
        user = User(
            tg_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            username=message.from_user.username,
            is_tg_premium=(
                message.from_user.is_premium if message.from_user.is_premium else False
            ),
            referred_by=ref_id,
            free_requests_left=DEFAULT_FREE_REQUESTS,
        )
        session.add(user)
        await session.commit()
        return user


async def get_referral_count(tg_id: int) -> int:
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.referred_by == tg_id))
        return len(result.scalars().all())


async def add_user_balance(tg_id: int, amount: float) -> User:
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        user.balance += amount
        await session.commit()
        return user


async def get_user_balance(tg_id: int) -> float:
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            return user.balance
        return 0.0


async def remove_user_balance(tg_id: int, amount: float) -> User:
    """
    Removes a specified amount from a user's balance if sufficient funds are available.

    This function deducts the given amount from the balance of a user identified
    by their Telegram ID. If the user's balance is less than the specified amount,
    an exception will be raised. The updated user object is returned upon successful
    completion of the transaction.

    Parameters:
        tg_id (int): Telegram ID of the user whose balance is to be modified.
        amount (float): The amount to deduct from the user's balance.

    Raises:
        ValueError: If the user's balance is insufficient.

    Returns:
        User: The updated user object reflecting the new balance.
    """
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user.balance >= amount:
            user.balance -= amount
            await session.commit()
            return user
        else:
            raise ValueError("Insufficient balance")


async def remove_token(message: Message) -> bool:
    async with get_general_session() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        if user.subscription_expiry and user.subscription_expiry > datetime.now():
            return True
        if user.free_requests_left > 0:
            user.free_requests_left -= 1
            await session.commit()
            return True
        if user.tokens > 0:
            user.tokens -= 1
            await session.commit()
            return True
        return False


async def add_tokens(user_id: int):
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()

        res = await session.execute(select(AdminRequirements))
        token_obj = res.scalar_one_or_none()
        token = token_obj.referral_count_for_free_month if token_obj else 10
        if user:
            user.tokens += token
            await session.commit()
            return user
        return None


async def update_user_premium_time(tg_id):
    async with get_general_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.subscription_expiry = (
                datetime.now()
                + timedelta(days=31)
                + timedelta(hours=23, minutes=59, seconds=59)
            )
            await session.commit()
            return user
        return None
