import json

import httpx
import pytest

from bot.db import Repository
from bot.xui import Inbound

TOKEN = "test-token"

STREAM = {
    "network": "tcp",
    "security": "reality",
    "realitySettings": {
        "serverNames": ["www.microsoft.com", "microsoft.com"],
        "shortIds": ["6ba85179e30d4fc2", "aa"],
        "settings": {"publicKey": "PUBKEY123", "fingerprint": "chrome", "spiderX": "/"},
    },
}

INBOUND = Inbound(id=1, port=443, protocol="vless", stream=STREAM)


def ok(obj=None) -> httpx.Response:
    return httpx.Response(200, json={"success": True, "msg": "", "obj": obj})


def fail(msg: str) -> httpx.Response:
    return httpx.Response(200, json={"success": False, "msg": msg, "obj": None})


class FakePanel:
    """In-memory imitation of the 3X-UI v3 REST API."""

    def __init__(self):
        self.clients: dict[str, dict] = {}
        self.inbound_ids: dict[str, list[int]] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401)
        path = request.url.path.removeprefix("/secret/panel/api")

        if path == "/inbounds/get/1":
            return ok(
                {"id": 1, "port": 443, "protocol": "vless", "streamSettings": json.dumps(STREAM)}
            )

        if path == "/clients/add":
            body = json.loads(request.content)
            client = body["client"]
            if client["email"] in self.clients:
                return fail("Duplicate email")
            self.clients[client["email"]] = client
            self.inbound_ids[client["email"]] = body["inboundIds"]
            return ok()

        action, _, email = path.removeprefix("/clients/").partition("/")
        if email not in self.clients:
            return ok() if action == "traffic" else fail("client not found")
        if action == "update":
            self.clients[email] = json.loads(request.content)
            return ok()
        if action == "del":
            del self.clients[email]
            return ok()
        if action == "traffic":
            client = self.clients[email]
            return ok(
                {
                    "email": email,
                    "up": 1024,
                    "down": 5 * 1024**2,
                    "enable": client["enable"],
                    "expiryTime": client["expiryTime"],
                }
            )
        return httpx.Response(404)


@pytest.fixture
def panel():
    return FakePanel()


@pytest.fixture
async def repo(tmp_path):
    repository = Repository(tmp_path / "bot.db")
    await repository.connect()
    yield repository
    await repository.close()
