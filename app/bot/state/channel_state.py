from aiogram.fsm.state import StatesGroup, State


class ChannelForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_link = State()
    waiting_for_id = State()
    waiting_for_active = State()


class ChannelUpdateForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_link = State()
