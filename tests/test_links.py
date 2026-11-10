from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import INBOUND

from bot.links import qr_png, vless_reality_link
from bot.texts import human_size
from bot.xui import Inbound


def test_vless_link():
    link = vless_reality_link("1111-2222", "vpn.example.com", INBOUND, "VPN 42")
    parts = urlsplit(link)

    assert parts.scheme == "vless"
    assert parts.netloc == "1111-2222@vpn.example.com:443"
    assert parts.fragment == "VPN%2042"
    params = {k: v[0] for k, v in parse_qs(parts.query).items()}
    assert params == {
        "type": "tcp",
        "security": "reality",
        "pbk": "PUBKEY123",
        "fp": "chrome",
        "sni": "www.microsoft.com",
        "sid": "6ba85179e30d4fc2",
        "spx": "/",
        "flow": "xtls-rprx-vision",
    }


def test_non_reality_inbound_rejected():
    inbound = Inbound(id=2, port=8443, protocol="vless", stream={"security": "tls"})
    with pytest.raises(ValueError):
        vless_reality_link("id", "host", inbound, "x")


def test_qr_is_png():
    assert qr_png("vless://test").startswith(b"\x89PNG")


@pytest.mark.parametrize(
    ("size", "expected"),
    [(512, "512 Б"), (2048, "2.0 КБ"), (5 * 1024**2, "5.0 МБ"), (3 * 1024**4, "3.0 ТБ")],
)
def test_human_size(size, expected):
    assert human_size(size) == expected
