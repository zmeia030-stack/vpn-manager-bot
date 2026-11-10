import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, Filter
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import Settings
from bot.handlers.common import send_key
from bot.keyboards import AccessDecision
from bot.service import AccessError, VpnService
from bot.texts import ADMIN_HELP, days_left, fmt_date, human_size


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject, settings: Settings) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and user.id in settings.admin_ids


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def parse_ints(command: CommandObject, required: int) -> list[int] | None:
    parts = (command.args or "").split()
    if len(parts) < required or not all(p.isdigit() for p in parts):
        return None
    return [int(p) for p in parts]


@router.message(Command("help"))
async def admin_help(message: Message):
    await message.answer(ADMIN_HELP)


@router.callback_query(AccessDecision.filter(F.action == "approve"))
async def approve(
    callback: CallbackQuery,
    callback_data: AccessDecision,
    bot: Bot,
    service: VpnService,
    settings: Settings,
):
    chat = await bot.get_chat(callback_data.tg_id)
    try:
        user = await service.grant(callback_data.tg_id, chat.username, settings.default_days)
    except AccessError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await send_key(bot, user, service)
    await callback.message.edit_text(
        f"{callback.message.html_text}\n\nОдобрено, доступ до {fmt_date(user.expires_at)}"
    )
    await callback.answer()


@router.callback_query(AccessDecision.filter(F.action == "deny"))
async def deny(callback: CallbackQuery, callback_data: AccessDecision, bot: Bot):
    await bot.send_message(callback_data.tg_id, "Заявка на доступ отклонена.")
    await callback.message.edit_text(f"{callback.message.html_text}\n\nОтклонено")
    await callback.answer()


@router.message(Command("users"))
async def list_users(message: Message, service: VpnService):
    users = await service.repo.all()
    if not users:
        await message.answer("Пользователей пока нет.")
        return
    traffic = await asyncio.gather(*(service.traffic(u) for u in users), return_exceptions=True)
    lines = []
    for user, usage in zip(users, traffic, strict=True):
        name = f"@{user.username}" if user.username else str(user.tg_id)
        used = human_size(usage.used) if usage and not isinstance(usage, Exception) else "?"
        state = "истёк" if user.is_expired else f"{days_left(user.expires_at)} дн."
        lines.append(f"<code>{user.tg_id}</code> {name}: {state}, {used}")
    await message.answer(f"Пользователей: {len(users)}\n\n" + "\n".join(lines))


@router.message(Command("add"))
async def add_user(
    message: Message, command: CommandObject, bot: Bot, service: VpnService, settings: Settings
):
    args = parse_ints(command, 1)
    if args is None:
        await message.answer("Формат: /add &lt;tg_id&gt; [дней]")
        return
    tg_id, days = args[0], args[1] if len(args) > 1 else settings.default_days
    try:
        user = await service.grant(tg_id, None, days)
    except AccessError as exc:
        await message.answer(str(exc))
        return
    await send_key(bot, user, service)
    await message.answer(f"Доступ выдан до {fmt_date(user.expires_at)}")


@router.message(Command("extend"))
async def extend_user(message: Message, command: CommandObject, bot: Bot, service: VpnService):
    args = parse_ints(command, 2)
    if args is None:
        await message.answer("Формат: /extend &lt;tg_id&gt; &lt;дней&gt;")
        return
    try:
        user = await service.extend(args[0], args[1])
    except AccessError as exc:
        await message.answer(str(exc))
        return
    await bot.send_message(user.tg_id, f"Доступ продлён до {fmt_date(user.expires_at)} (МСК).")
    await message.answer(f"Продлено до {fmt_date(user.expires_at)}")


@router.message(Command("revoke"))
async def revoke_user(message: Message, command: CommandObject, service: VpnService):
    args = parse_ints(command, 1)
    if args is None:
        await message.answer("Формат: /revoke &lt;tg_id&gt;")
        return
    try:
        await service.revoke(args[0])
    except AccessError as exc:
        await message.answer(str(exc))
        return
    await message.answer("Доступ отозван, клиент удалён из панели.")
