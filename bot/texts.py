import math
from datetime import UTC, datetime, timedelta, timezone

from bot.db import VpnUser
from bot.xui import ClientTraffic

MSK = timezone(timedelta(hours=3))


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if value < 1024:
            return f"{value:.0f} {unit}" if unit == "Б" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} ТБ"


def fmt_date(value: datetime) -> str:
    return value.astimezone(MSK).strftime("%d.%m.%Y %H:%M")


def days_left(value: datetime) -> int:
    seconds = (value - datetime.now(UTC)).total_seconds()
    return max(math.ceil(seconds / 86400), 0)


def status_text(user: VpnUser, traffic: ClientTraffic | None) -> str:
    lines = [
        f"Доступ до: <b>{fmt_date(user.expires_at)}</b> (МСК)",
        "Статус: истёк" if user.is_expired else f"Осталось дней: {days_left(user.expires_at)}",
    ]
    if traffic is not None:
        lines.append(
            f"Трафик: {human_size(traffic.used)} "
            f"(↓ {human_size(traffic.down)}, ↑ {human_size(traffic.up)})"
        )
    return "\n".join(lines)


KEY_CAPTION = (
    "Ключ действует до {expires} (МСК).\n\n"
    "Отсканируй QR-код в приложении (v2rayNG, Hiddify, Streisand, v2RayTun) "
    "или скопируй ссылку:\n<code>{link}</code>"
)

USER_HELP = "Доступ активен.\n/key — ключ и QR-код\n/status — срок действия и трафик"

ADMIN_HELP = (
    "Команды администратора:\n"
    "/users — список пользователей\n"
    "/add &lt;tg_id&gt; [дней] — выдать доступ\n"
    "/extend &lt;tg_id&gt; &lt;дней&gt; — продлить\n"
    "/revoke &lt;tg_id&gt; — отозвать доступ"
)
