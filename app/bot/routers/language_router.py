from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _

from app.bot.handlers.user_handlers import get_user_by_tg_id, update_user_by_tg_id
from app.bot.keyboards.language_keyboard import language_keyboard
from app.bot.models import User

language_router = Router()


@language_router.message(F.text == "/lang")
async def ask_language(message: Message):
    user: User = await get_user_by_tg_id(message.from_user.id)
    current_lang = user.language_code
    kb = await language_keyboard(selected_lang=current_lang)
    await message.answer(_("lang_choose"), reply_markup=kb)


@language_router.callback_query(F.data.startswith("set_lang:"))
async def on_language_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang_code = callback.data.split(":")[1]
    await update_user_by_tg_id(user_id, {"language_code": lang_code})
    await callback.message.delete()
    await callback.message.answer(_("start"))


@language_router.message(Command("developer"))
async def handle_developer_command(message: Message):
    await message.answer(
        _("developer_info"),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )
