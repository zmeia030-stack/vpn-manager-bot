from datetime import UTC, datetime, timedelta

import httpx
import pytest
from conftest import TOKEN

from bot.reminders import send_reminders
from bot.service import AccessError, VpnService
from bot.xui import XUIClient


@pytest.fixture
async def service(panel, repo):
    xui = XUIClient(
        "https://panel.local/secret", TOKEN, transport=httpx.MockTransport(panel.handler)
    )
    yield VpnService(xui, repo, inbound_id=1, server_host="vpn.example.com")
    await xui.close()


async def test_grant_creates_panel_client(service, panel):
    user = await service.grant(42, "andrey", days=30)

    assert user.email == "tg42"
    assert panel.clients["tg42"]["id"] == user.client_id
    assert (await service.get_user(42)).username == "andrey"
    assert (await service.link(user)).startswith(f"vless://{user.client_id}@vpn.example.com:443")


async def test_grant_twice_fails(service):
    await service.grant(42, None, days=30)
    with pytest.raises(AccessError):
        await service.grant(42, None, days=30)


async def test_extend_adds_days_to_current_expiry(service, panel):
    user = await service.grant(42, None, days=10)
    extended = await service.extend(42, days=30)

    assert extended.expires_at - user.expires_at == timedelta(days=30)
    expected_ms = int(extended.expires_at.timestamp() * 1000)
    assert panel.clients["tg42"]["expiryTime"] == expected_ms


async def test_extend_expired_counts_from_now(service, repo):
    await service.grant(42, None, days=1)
    await repo.set_expiry(42, datetime.now(UTC) - timedelta(days=5))

    extended = await service.extend(42, days=7)
    assert extended.expires_at > datetime.now(UTC) + timedelta(days=6)


async def test_revoke(service, panel):
    await service.grant(42, None, days=30)
    await service.revoke(42)
    assert panel.clients == {}
    assert await service.get_user(42) is None
    with pytest.raises(AccessError):
        await service.revoke(42)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append(chat_id)


async def test_reminders_sent_once(service, repo):
    await service.grant(1, None, days=2)
    await service.grant(2, None, days=20)
    bot = FakeBot()

    assert await send_reminders(bot, repo, before_days=3) == 1
    assert await send_reminders(bot, repo, before_days=3) == 0
    assert bot.sent == [1]

    await service.extend(1, days=1)
    assert await send_reminders(bot, repo, before_days=3) == 1
