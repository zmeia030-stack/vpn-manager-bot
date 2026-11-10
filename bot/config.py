from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: SecretStr
    admin_ids: list[int]

    panel_url: str
    panel_api_token: SecretStr
    panel_verify_ssl: bool = True
    inbound_id: int
    server_host: str

    db_path: Path = Path("data/bot.db")
    default_days: int = 30
    remind_before_days: int = 3
