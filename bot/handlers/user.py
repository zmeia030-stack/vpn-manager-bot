from aiogram import Bot, F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.common import send_key
from bot.keyboards import REQUEST_ACCESS, decision_keyboard, request_keyboard
from bot.service import VpnService
from bot.texts import USER_HELP, status_text

router = Router()

NO_ACCESS = "Доступа пока нет. Нажми /start, чтобы отправить заявку."


@router.message(CommandStart())
async def start(message: Message, service: VpnService):
    if await service.get_user(message.from_user.id):
        await message.answer(USER_HELP)
        return
    await message.answer(
        "Привет! Через этого бота выдаётся доступ к VPN.\n"
        "Нажми кнопку ниже, и администратор получит заявку.",
        reply_markup=request_keyboard(),
    )


@router.callback_query(F.data == REQUEST_ACCESS)
async def request_access(
    callback: CallbackQuery, bot: Bot, service: VpnService, settings: Settings
):
    person = callback.from_user
    if await service.get_user(person.id):
        await callback.answer("У тебя уже есть доступ", show_alert=True)
        return

    username = f"@{person.username}" if person.username else "без username"
    text = (
        f"Заявка на доступ\n{html.quote(person.full_name)} ({username})\n"
        f"id: <code>{person.id}</code>"
    )
    for admin_id in settings.admin_ids:
        await bot.send_message(
            admin_id, text, reply_markup=decision_keyboard(person.id, settings.default_days)
        )
    await callback.message.edit_text("Заявка отправлена. Как только её одобрят, придёт ключ.")
    await callback.answer()


@router.message(Command("key"))
async def key(message: Message, bot: Bot, service: VpnService):
    user = await service.get_user(message.from_user.id)
    if user is None:
        await message.answer(NO_ACCESS)
        return
    await send_key(bot, user, service)


@router.message(Command("status"))
async def status(message: Message, service: VpnService):
    user = await service.get_user(message.from_user.id)
    if user is None:
        await message.answer(NO_ACCESS)
        return
    await message.answer(status_text(user, await service.traffic(user)))
