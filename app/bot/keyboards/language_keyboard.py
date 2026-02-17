from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


async def language_keyboard(selected_lang: str | None) -> InlineKeyboardMarkup:
    languages = [
        ("English", "en"),
        ("Русский", "ru"),
        ("O‘zbek", "uz"),
        ("Ўзбек", "kr"),
    ]

    buttons = []
    row = []
    for i, (name, code) in enumerate(languages, 1):
        label = f"{name} ✅" if code == selected_lang else name
        row.append(InlineKeyboardButton(text=label, callback_data=f"set_lang:{code}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
