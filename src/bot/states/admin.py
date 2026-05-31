from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_user_search = State()
    waiting_for_subscription_user_id = State()
