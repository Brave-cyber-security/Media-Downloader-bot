from aiogram.fsm.state import StatesGroup, State


class SettingsForm(StatesGroup):
    waiting_for_token = State()


class BroadcastForm(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()
