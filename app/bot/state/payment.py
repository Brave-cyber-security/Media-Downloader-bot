from aiogram.fsm.state import StatesGroup, State


class FillBalanceStates(StatesGroup):
    waiting_for_tg_id = State()
    waiting_for_amount = State()


class UnFillBalanceStates(StatesGroup):
    waiting_for_tg_id = State()
    waiting_for_amount = State()
