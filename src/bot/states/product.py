from aiogram.fsm.state import State, StatesGroup


class AddProductState(StatesGroup):
    waiting_for_url = State()
    waiting_for_target_price = State()


class EditProductState(StatesGroup):
    waiting_for_target_price = State()
    waiting_for_threshold = State()
