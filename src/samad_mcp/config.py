from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "https://food.guilan.ac.ir"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    base_url: str = DEFAULT_BASE_URL


def load_settings() -> Settings:
    load_dotenv(_PROJECT_ROOT / ".env")
    username = os.getenv("SAMAD_USERNAME", "").strip()
    password = os.getenv("SAMAD_PASSWORD", "")
    base_url = (os.getenv("SAMAD_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    if not username or not password:
        raise ConfigError(
            "نام کاربری یا رمز عبور تنظیم نشده است. "
            f"فایل .env را در مسیر {_PROJECT_ROOT / '.env'} باز کن و "
            "SAMAD_USERNAME و SAMAD_PASSWORD را پر کن."
        )
    return Settings(username=username, password=password, base_url=base_url)