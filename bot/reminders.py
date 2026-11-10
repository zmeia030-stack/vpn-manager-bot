import asyncio
import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.db import Repository
from bot.texts import fmt_date

log = logging.getLogger(__name__)


async def send_reminders(bot: Bot, repo: Repository, before_days: int) -> int:
    deadline = datetime.now(UTC) + timedelta(days=before_days)
    users = await repo.expiring_before(deadline)
    for user in users:
        try:
            await bot.send_message(
                user.tg_id,
                f"Доступ к VPN закончится {fmt_date(user.expires_at)} (МСК). "
                "Напиши администратору, если нужно продлить.",
            )
        except TelegramAPIError as exc:
            log.warning("Could not remind %s: %s", user.tg_id, exc)
        await repo.mark_reminded(user.tg_id)
    return len(users)


async def reminder_loop(bot: Bot, repo: Repository, before_days: int, interval: int = 3600):
    while True:
        try:
            sent = await send_reminders(bot, repo, before_days)
            if sent:
                log.info("Sent %d expiry reminders", sent)
        except Exception:
            log.exception("Reminder check failed")
        await asyncio.sleep(interval)
