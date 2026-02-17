from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from app.bot.handlers.statistics_handler import create_statistics
from app.bot.handlers.user_handlers import (
    get_user_by_tg_id,
    create_user,
    add_tokens,
)
from app.bot.keyboards.general_buttons import main_menu_keyboard
from app.bot.keyboards.language_keyboard import language_keyboard
from app.bot.models import User

start_router = Router()


async def start_function(message: Message, ref_id=None):
    await create_user(message, ref_id)
    user: User = await get_user_by_tg_id(message.from_user.id)
    if user.language_code is None:
        kb = await language_keyboard(selected_lang=None)
        await message.answer(_("start_welcome"), reply_markup=kb)
    else:
        await message.answer(_("start"), reply_markup=main_menu_keyboard(message))


@start_router.message(CommandStart(deep_link=True))
async def handle_start_deep_link(message: Message, command: CommandStart):
    user = await get_user_by_tg_id(message.from_user.id)
    referrer_id = command.args if command.args and command.args.isdigit() else None
    if user is None:
        if referrer_id:
            inviter = await get_user_by_tg_id(int(referrer_id))
            if inviter is None:
                referrer_id = None
            else:
                referrer_id = inviter.tg_id
                await add_tokens(referrer_id)
            await start_function(message, referrer_id)
        else:
            await start_function(message)
    else:
        await start_function(message)
    await create_statistics(message.from_user.id)


@start_router.message(CommandStart())
async def handle_start(message: Message):
    await start_function(message)


@start_router.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(
        _("help_message"),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(message),
    )
