from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

REQUEST_ACCESS = "request_access"


class AccessDecision(CallbackData, prefix="access"):
    action: str
    tg_id: int


def request_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Запросить доступ", callback_data=REQUEST_ACCESS)
    return builder.as_markup()


def decision_keyboard(tg_id: int, days: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Выдать на {days} дн.", callback_data=AccessDecision(action="approve", tg_id=tg_id)
    )
    builder.button(text="Отклонить", callback_data=AccessDecision(action="deny", tg_id=tg_id))
    return builder.as_markup()
