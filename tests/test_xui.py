from datetime import UTC, datetime, timedelta

import httpx
import pytest
from conftest import TOKEN

from bot.xui import XUIClient, XUIError


def make_client(panel, token=TOKEN) -> XUIClient:
    return XUIClient(
        "https://panel.example.com:2053/secret/",
        token,
        transport=httpx.MockTransport(panel.handler),
    )


async def test_add_client_and_traffic(panel):
    xui = make_client(panel)
    expires = datetime(2030, 1, 1, tzinfo=UTC)
    client_id = await xui.add_client(1, "tg42", expires, tg_id=42)

    stored = panel.clients["tg42"]
    assert stored["id"] == client_id
    assert stored["flow"] == "xtls-rprx-vision"
    assert stored["tgId"] == 42
    assert stored["expiryTime"] == int(expires.timestamp() * 1000)
    assert panel.inbound_ids["tg42"] == [1]

    traffic = await xui.get_traffic("tg42")
    assert traffic.used == 1024 + 5 * 1024**2
    assert traffic.expires_at == expires
    await xui.close()


async def test_get_inbound(panel):
    xui = make_client(panel)
    inbound = await xui.get_inbound(1)
    assert (inbound.port, inbound.protocol) == (443, "vless")
    assert inbound.stream["security"] == "reality"
    await xui.close()


async def test_invalid_token(panel):
    xui = make_client(panel, token="wrong")
    with pytest.raises(XUIError, match="token"):
        await xui.get_inbound(1)
    await xui.close()


async def test_panel_error_message_is_raised(panel):
    xui = make_client(panel)
    expires = datetime.now(UTC) + timedelta(days=1)
    await xui.add_client(1, "tg1", expires)
    with pytest.raises(XUIError, match="Duplicate email"):
        await xui.add_client(1, "tg1", expires)
    await xui.close()


async def test_update_and_delete(panel):
    xui = make_client(panel)
    expires = datetime.now(UTC) + timedelta(days=1)
    client_id = await xui.add_client(1, "tg1", expires)
    await xui.update_client(client_id, "tg1", expires, enable=False)
    assert panel.clients["tg1"]["enable"] is False

    await xui.delete_client("tg1")
    assert panel.clients == {}
    assert await xui.get_traffic("tg1") is None
    await xui.close()


async def test_unreachable_panel():
    def refuse(request):
        raise httpx.ConnectError("connection refused")

    xui = XUIClient("https://panel.local", TOKEN, transport=httpx.MockTransport(refuse))
    with pytest.raises(XUIError, match="unreachable"):
        await xui.get_inbound(1)
    await xui.close()
