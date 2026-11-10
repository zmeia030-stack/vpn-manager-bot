from io import BytesIO
from urllib.parse import quote, urlencode

import qrcode

from bot.xui import FLOW, Inbound


def vless_reality_link(client_id: str, host: str, inbound: Inbound, remark: str) -> str:
    stream = inbound.stream
    if inbound.protocol != "vless" or stream.get("security") != "reality":
        raise ValueError("Only VLESS + Reality inbounds are supported")

    reality = stream["realitySettings"]
    params = {
        "type": stream.get("network", "tcp"),
        "security": "reality",
        "pbk": reality["settings"]["publicKey"],
        "fp": reality["settings"].get("fingerprint") or "chrome",
        "sni": reality["serverNames"][0],
        "sid": reality["shortIds"][0],
        "spx": reality["settings"].get("spiderX") or "/",
        "flow": FLOW,
    }
    return f"vless://{client_id}@{host}:{inbound.port}?{urlencode(params)}#{quote(remark)}"


def qr_png(data: str) -> bytes:
    buffer = BytesIO()
    qrcode.make(data, box_size=8, border=2).save(buffer, format="PNG")
    return buffer.getvalue()
