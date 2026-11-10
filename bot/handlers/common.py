from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.db import VpnUser
from bot.links import qr_png
from bot.service import VpnService
from bot.texts import KEY_CAPTION, fmt_date


async def send_key(bot: Bot, user: VpnUser, service: VpnService) -> None:
    link = await service.link(user)
    await bot.send_photo(
        user.tg_id,
        BufferedInputFile(qr_png(link), filename="vpn-key.png"),
        caption=KEY_CAPTION.format(expires=fmt_date(user.expires_at), link=link),
    )
