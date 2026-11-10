import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import BotCommand, ErrorEvent

from bot.config import Settings
from bot.db import Repository
from bot.handlers import admin, user
from bot.reminders import reminder_loop
from bot.service import VpnService
from bot.xui import XUIClient, XUIError

log = logging.getLogger("bot")


async def on_panel_error(event: ErrorEvent) -> None:
    log.error("3X-UI error: %s", event.exception)
    update = event.update
    target = update.message or (update.callback_query and update.callback_query.message)
    if target:
        await target.answer("Панель VPN сейчас недоступна, попробуй позже.")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = Settings()

    repo = Repository(settings.db_path)
    await repo.connect()
    xui = XUIClient(
        settings.panel_url,
        settings.panel_api_token.get_secret_value(),
        verify_ssl=settings.panel_verify_ssl,
    )
    service = VpnService(xui, repo, settings.inbound_id, settings.server_host)

    bot = Bot(
        settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="key", description="Мой ключ и QR-код"),
            BotCommand(command="status", description="Срок действия и трафик"),
        ]
    )

    dp = Dispatcher(service=service, settings=settings)
    dp.errors.register(on_panel_error, ExceptionTypeFilter(XUIError))
    dp.include_routers(admin.router, user.router)

    reminders = asyncio.create_task(reminder_loop(bot, repo, settings.remind_before_days))
    try:
        await dp.start_polling(bot)
    finally:
        reminders.cancel()
        await xui.close()
        await repo.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
