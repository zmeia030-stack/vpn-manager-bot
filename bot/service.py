from datetime import UTC, datetime, timedelta

from bot.db import Repository, VpnUser
from bot.links import vless_reality_link
from bot.xui import ClientTraffic, XUIClient


def now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class AccessError(Exception):
    pass


class VpnService:
    def __init__(self, xui: XUIClient, repo: Repository, inbound_id: int, server_host: str):
        self.xui = xui
        self.repo = repo
        self.inbound_id = inbound_id
        self.server_host = server_host

    async def get_user(self, tg_id: int) -> VpnUser | None:
        return await self.repo.get(tg_id)

    async def grant(self, tg_id: int, username: str | None, days: int) -> VpnUser:
        if await self.repo.get(tg_id) is not None:
            raise AccessError("У пользователя уже есть доступ")
        email = f"tg{tg_id}"
        expires_at = now_utc() + timedelta(days=days)
        client_id = await self.xui.add_client(self.inbound_id, email, expires_at, tg_id)
        user = VpnUser(tg_id, username, client_id, email, expires_at)
        await self.repo.add(user)
        return user

    async def extend(self, tg_id: int, days: int) -> VpnUser:
        user = await self._require(tg_id)
        start = max(user.expires_at, now_utc())
        user.expires_at = start + timedelta(days=days)
        await self.xui.update_client(user.client_id, user.email, user.expires_at, user.tg_id)
        await self.repo.set_expiry(tg_id, user.expires_at)
        return user

    async def revoke(self, tg_id: int) -> None:
        user = await self._require(tg_id)
        await self.xui.delete_client(user.email)
        await self.repo.delete(tg_id)

    async def link(self, user: VpnUser) -> str:
        inbound = await self.xui.get_inbound(self.inbound_id)
        return vless_reality_link(user.client_id, self.server_host, inbound, f"VPN-{user.tg_id}")

    async def traffic(self, user: VpnUser) -> ClientTraffic | None:
        return await self.xui.get_traffic(user.email)

    async def _require(self, tg_id: int) -> VpnUser:
        user = await self.repo.get(tg_id)
        if user is None:
            raise AccessError("У пользователя нет доступа")
        return user
