import os
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.enums.chat_action import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _

from app.bot.controller.admin_controller import export_users_to_excel
from app.bot.filters.admin_filter import AdminFilter
from app.bot.handlers.admin import (
    get_last_7_days_statistics,
    get_premium_price,
    get_token_per_referral,
)
from app.bot.handlers.channel_handler import get_all_channels
from app.bot.handlers.statistics_handler import get_all_statistics
from app.bot.keyboards.admin_keyboards import (
    get_admin_panel_keyboard,
    get_channel_crud_keyboard,
)
from app.bot.keyboards.general_buttons import main_menu_keyboard
from app.bot.models import Channel

main_menu_router = Router()


@main_menu_router.message(AdminFilter(), F.text.contains("Admin Panel"))
async def handle_admin_panel(message: Message):
    await message.answer(
        _("admin_panel_welcome"),
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML",
    )


@main_menu_router.message(AdminFilter(), F.text == "📁 Users excel")
async def handle_statistics(message: Message):
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)
    file_path: str = await export_users_to_excel()
    try:
        file_name = "Users_report.xlsx"

        doc = FSInputFile(path=file_path, filename=file_name)
        caption = _("user_export_caption").format(
            file_name=file_name,
            generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        await message.answer_document(document=doc, caption=caption, parse_mode="HTML")

    except Exception as err:
        await message.answer(
            _("export_failed_error").format(error=err), parse_mode="HTML"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@main_menu_router.message(AdminFilter(), F.text == "📊 Statistics")
async def handle_last_users(message: Message):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    stats = await get_last_7_days_statistics()
    channels: list[Channel] = await get_all_channels()
    statistics = await get_all_statistics()

    lines = [
        _("user_growth_header"),
        _("stats_today").format(count=stats["today"]),
        _("stats_yesterday").format(count=stats["yesterday"]),
        _("stats_last_week").format(count=stats["last_week"]),
        _("stats_last_month").format(count=stats["last_month"]),
        _("stats_last_year").format(count=stats["last_year"]),
        _("stats_all_time").format(count=stats["all_time"]),
        "",
    ]

    if stats["top_referrers"]:
        lines.append(_("top_referrers_header"))
        for idx, ref in enumerate(stats["top_referrers"], start=1):
            lines.append(
                _("referrer_item").format(
                    idx=idx, name=ref["name"], tg_id=ref["tg_id"], count=ref["count"]
                )
            )

    if channels:
        lines.append(_("connected_channels_header"))
        for idx, ch in enumerate(channels, start=1):
            status = _("channel_active") if ch.is_active else _("channel_inactive")
            lines.append(
                _("channel_item").format(
                    idx=idx, link=ch.link, name=ch.name, status=status
                )
            )
    else:
        lines.append(_("no_channels_connected"))

    lines.append(_("usage_statistics_header"))
    lines.append(_("usage_from_text").format(count=statistics["from_text"]))
    lines.append(_("usage_from_voice").format(count=statistics["from_voice"]))
    lines.append(_("usage_from_youtube").format(count=statistics["from_youtube"]))
    lines.append(_("usage_from_tiktok").format(count=statistics["from_tiktok"]))
    lines.append(_("usage_from_like").format(count=statistics["from_like"]))
    lines.append(_("usage_from_snapchat").format(count=statistics["from_snapchat"]))
    lines.append(_("usage_from_instagram").format(count=statistics["from_instagram"]))
    lines.append(_("usage_from_twitter").format(count=statistics["from_twitter"]))

    await message.answer(
        "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True
    )
    await message.answer(
        _("current_token_and_price").format(
            tokens=await get_token_per_referral(), price=await get_premium_price()
        ),
        parse_mode="HTML",
    )


@main_menu_router.message(AdminFilter(), F.text == "🔧 Settings")
async def handle_settings(message: Message):
    await message.answer(_("settings_page"), parse_mode="HTML")


@main_menu_router.message(AdminFilter(), F.text == "📈 Channels")
async def handle_channels(message: Message):
    await message.answer(
        _("channels_page"), parse_mode="HTML", reply_markup=get_channel_crud_keyboard()
    )


@main_menu_router.message(AdminFilter(), F.text.contains("Back to Admin Panel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        _("broadcast_cancelled"), reply_markup=get_admin_panel_keyboard()
    )


@main_menu_router.message(AdminFilter(), F.text == "🔙 Back to Main Menu")
async def handle_back_to_admin_panel(message: Message):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    await message.answer(
        text=_("back_to_admin_panel_welcome"),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(message),
    )

