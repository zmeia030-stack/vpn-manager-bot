"""Minimal async client for the 3X-UI v3 panel API (Bearer token auth)."""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

FLOW = "xtls-rprx-vision"


class XUIError(Exception):
    pass


@dataclass
class Inbound:
    id: int
    port: int
    protocol: str
    stream: dict


@dataclass
class ClientTraffic:
    email: str
    up: int
    down: int
    enabled: bool
    expires_at: datetime | None

    @property
    def used(self) -> int:
        return self.up + self.down


def to_millis(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def from_millis(value: int) -> datetime | None:
    return datetime.fromtimestamp(value / 1000, UTC) if value > 0 else None


class XUIClient:
    def __init__(
        self,
        base_url: str,
        api_token: str,
        verify_ssl: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._http = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/panel/api",
            headers={"Authorization": f"Bearer {api_token}"},
            verify=verify_ssl,
            timeout=10,
            transport=transport,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise XUIError(f"Panel is unreachable: {exc}") from exc
        if response.status_code == 401:
            raise XUIError("API token is invalid or disabled")
        if response.status_code != 200:
            raise XUIError(f"{method} {path}: HTTP {response.status_code}")
        data = response.json()
        if not data.get("success"):
            raise XUIError(data.get("msg") or f"{method} {path} failed")
        return data.get("obj")

    async def get_inbound(self, inbound_id: int) -> Inbound:
        obj = await self._request("GET", f"/inbounds/get/{inbound_id}")
        return Inbound(
            id=obj["id"],
            port=obj["port"],
            protocol=obj["protocol"],
            stream=json.loads(obj["streamSettings"]),
        )

    async def add_client(
        self, inbound_id: int, email: str, expires_at: datetime, tg_id: int = 0
    ) -> str:
        client_id = str(uuid.uuid4())
        client = _client(client_id, email, expires_at, tg_id)
        await self._request(
            "POST", "/clients/add", json={"client": client, "inboundIds": [inbound_id]}
        )
        return client_id

    async def update_client(
        self,
        client_id: str,
        email: str,
        expires_at: datetime,
        tg_id: int = 0,
        enable: bool = True,
    ) -> None:
        client = _client(client_id, email, expires_at, tg_id, enable)
        await self._request("POST", f"/clients/update/{email}", json=client)

    async def delete_client(self, email: str) -> None:
        await self._request("POST", f"/clients/del/{email}")

    async def get_traffic(self, email: str) -> ClientTraffic | None:
        obj = await self._request("GET", f"/clients/traffic/{email}")
        if not obj:
            return None
        return ClientTraffic(
            email=obj["email"],
            up=obj["up"],
            down=obj["down"],
            enabled=obj["enable"],
            expires_at=from_millis(obj["expiryTime"]),
        )


def _client(
    client_id: str, email: str, expires_at: datetime, tg_id: int, enable: bool = True
) -> dict:
    return {
        "id": client_id,
        "email": email,
        "flow": FLOW,
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": to_millis(expires_at),
        "enable": enable,
        "tgId": tg_id,
        "subId": client_id.replace("-", "")[:16],
    }
