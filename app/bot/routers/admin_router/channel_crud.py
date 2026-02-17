from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import IntegrityError
from aiogram.enums.chat_action import ChatAction
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.i18n import gettext as _

from app.bot.keyboards.admin_keyboards import get_channel_crud_keyboard
from app.bot.state.channel_state import ChannelForm, ChannelUpdateForm
from app.bot.filters.admin_filter import AdminFilter
from app.bot.handlers.channel_handler import (
    delete_channel,
    get_channel_by_id,
    update_channel,
    add_channel,
    fetch_unsubscribed_channels,
)
from app.bot.keyboards.channels_keyboards import (
    channels_list_keyboard,
    confirm_keyboard,
    skip_kb,
)

channel_router = Router()


@channel_router.message(F.text == "📋 View Channels")
async def handle_channel_list(message: Message):
    text = (
        _("📋 <b>Channel List</b>")
        + "\n\n"
        + _("Here you can view the list of channels that have been added.")
        + "\n"
        + _("Use the buttons below to manage your channels.")
    )
    await message.answer(
        text, parse_mode="HTML", reply_markup=await channels_list_keyboard()
    )


@channel_router.callback_query(F.data.startswith("channel:delete:"))
async def handle_delete_channel(callback_query: CallbackQuery):
    channel_id = int(callback_query.data.split(":")[-1])
    await delete_channel(channel_id)
    await callback_query.message.edit_reply_markup(
        reply_markup=await channels_list_keyboard()
    )
    await callback_query.answer(
        _("🗑️ Channel %(channel_id)d deleted.") % {"channel_id": channel_id},
        show_alert=False,
    )


@channel_router.callback_query(F.data.startswith("channel:info:"))
async def handle_channel_info(callback_query: CallbackQuery):
    channel_id = int(callback_query.data.split(":")[-1])
    channel = await get_channel_by_id(channel_id)

    if not channel:
        await callback_query.answer(_("❌ Channel not found."), show_alert=True)
        return

    status_text = _("Active") if channel.is_active else _("Inactive")
    text = (
        _("📺 <b>Channel Info</b>")
        + "\n\n"
        + _("<b>Name:</b> %(name)s") % {"name": channel.name}
        + "\n"
        + _("<b>Link:</b> %(link)s") % {"link": channel.link}
        + "\n"
        + _("<b>Status:</b> %(status)s") % {"status": status_text}
        + "\n"
    )

    await callback_query.message.edit_text(
        text, parse_mode="HTML", reply_markup=await channels_list_keyboard()
    )
    await callback_query.answer()


@channel_router.callback_query(F.data.startswith("channel:toggle:"))
async def handle_toggle_channel(callback_query: CallbackQuery):
    channel_id = int(callback_query.data.split(":")[-1])
    channel = await get_channel_by_id(channel_id)
    if not channel:
        await callback_query.answer(_("❌ Channel not found."), show_alert=True)
        return
    if channel.is_active:
        await update_channel(channel_id, is_active=False)
    else:
        await update_channel(channel_id, is_active=True)
    await callback_query.message.edit_reply_markup(
        reply_markup=await channels_list_keyboard()
    )


@channel_router.message(AdminFilter(), F.text == "➕ Add Channel")
async def start_add_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        _("📣 Please send the <b>channel name</b>:"),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ChannelForm.waiting_for_name)


@channel_router.message(ChannelForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        _("🔗 Now send the <b>channel link</b> (e.g. https://t.me/yourchannel):"),
        parse_mode="HTML",
    )
    await state.set_state(ChannelForm.waiting_for_link)


@channel_router.message(ChannelForm.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await message.answer(
        _("🆔 Please send the <b>numeric channel ID</b> (only digits):"),
        parse_mode="HTML",
    )
    await state.set_state(ChannelForm.waiting_for_id)


@channel_router.message(ChannelForm.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    text = message.text.strip()

    try:
        channel_id = int(text)
        if not str(channel_id).startswith("-100") or len(str(channel_id)) < 10:
            raise ValueError("Invalid format")

        await state.update_data(channel_id=channel_id)
        await message.answer(
            _("✅ Should this channel be active?"),
            parse_mode="HTML",
            reply_markup=confirm_keyboard(),
        )
        await state.set_state(ChannelForm.waiting_for_active)

    except ValueError:
        await message.answer(
            _(
                "❗️ Please send a valid numeric channel ID (example: <code>-1001234567890</code>)."
            ),
            parse_mode="HTML",
        )


@channel_router.callback_query(ChannelForm.waiting_for_active, F.data.startswith("channel_active:"))
async def process_active(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[-1]
    is_active = action == "yes"

    await callback.answer()

    data = await state.get_data()
    try:
        channel = await add_channel(
            name=data["name"],
            link=data["link"],
            channel_id=data["channel_id"],
            is_active=is_active,
        )

    except IntegrityError as e:
        if "channels_link_key" in str(e.orig):
            await callback.message.answer(
                _(
                    "⚠️ That link is already in use. Please start over with a unique channel link."
                ),
                parse_mode="HTML",
                reply_markup=get_channel_crud_keyboard(),
            )
        elif "channels_channel_id_key" in str(e.orig):
            await callback.message.answer(
                _(
                    "⚠️ That channel ID is already in use. Please start over with a unique ID."
                ),
                parse_mode="HTML",
                reply_markup=get_channel_crud_keyboard(),
            )
        else:
            await callback.message.answer(
                _("❌ Database error:\n<code>%(error)s</code>") % {"error": e.orig},
                parse_mode="HTML",
                reply_markup=get_channel_crud_keyboard(),
            )
        await state.clear()
        return

    await callback.message.answer(
        _(
            "🎉 Channel <b>%(name)s</b> has been added successfully!\nMake sure to set the channel's privacy settings to allow the bot to access it."
        )
        % {"name": channel.name},
        parse_mode="HTML",
        reply_markup=get_channel_crud_keyboard(),
    )
    await state.clear()


@channel_router.callback_query(AdminFilter(), F.data.startswith("channel:update:"))
async def start_update_channel(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[-1])
    await state.clear()
    await state.update_data(channel_id=channel_id)

    await callback.answer()
    await callback.message.answer(
        text=_(
            "✏️ <b>Update Channel Name</b>\n\nSend the new name or tap ⏭ Skip to keep the old one:"
        ),
        parse_mode="HTML",
        reply_markup=skip_kb("⏭ Skip"),
    )
    await state.set_state(ChannelUpdateForm.waiting_for_name)


@channel_router.message(AdminFilter(), ChannelUpdateForm.waiting_for_name)
async def process_update_name(message: Message, state: FSMContext):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    text = message.text.strip()

    if text == "⏭ Skip":
        data = await state.get_data()
        channel = await get_channel_by_id(data["channel_id"])
        await state.update_data(name=channel.name)
    else:
        await state.update_data(name=text)

    await message.answer(
        text=_(
            "🔗 <b>Update Channel Link</b>\n\nSend the new link or tap ⏭ Skip to keep the old one:"
        ),
        parse_mode="HTML",
        reply_markup=skip_kb("⏭ Skip"),
    )
    await state.set_state(ChannelUpdateForm.waiting_for_link)


@channel_router.message(AdminFilter(), ChannelUpdateForm.waiting_for_link)
async def process_update_link(message: Message, state: FSMContext):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    text = message.text.strip()
    data = await state.get_data()

    if text == "⏭ Skip":
        channel = await get_channel_by_id(data["channel_id"])
        new_link = channel.link
    else:
        new_link = text

    try:
        updated = await update_channel(
            data["channel_id"], name=data["name"], link=new_link
        )
    except IntegrityError as err:
        if "channels_link_key" in str(err.orig):
            await message.answer(
                text=_("⚠️ That link exists. Send a unique link or tap ⏭ Skip:"),
                parse_mode="HTML",
                reply_markup=skip_kb("⏭ Skip"),
            )
            return
        await message.answer(
            text=_("❌ DB error:\n<code>%(error)s</code>") % {"error": err.orig},
            parse_mode="HTML",
        )
        await state.clear()
        return

    await message.answer(
        text=_("✅ Channel <b>%(name)s</b> updated!\n🔗 Link: <code>%(link)s</code>")
        % {"name": updated.name, "link": updated.link},
        parse_mode="HTML",
        reply_markup=get_channel_crud_keyboard(),
    )
    await state.clear()


from app.bot.keyboards.channels_keyboards import get_channel_keyboard


@channel_router.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    bot = callback_query.bot

    unsubscribed = await fetch_unsubscribed_channels(user_id, bot)

    if unsubscribed:
        kb = await get_channel_keyboard(unsubscribed)
        try:
            await callback_query.message.edit_text(
                text=_("🚫 You still need to join these channels."), reply_markup=kb
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
    else:
        try:
            await callback_query.message.delete()
        except TelegramBadRequest as e:
            pass
        await callback_query.message.answer("start")
