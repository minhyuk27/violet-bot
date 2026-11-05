import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # 2단계부터 적용할 화이트리스트 (쉼표 구분 user ID 문자열)
    ALLOWED_USER_IDS: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()
    ])

    VAULT_DIR: str = os.path.expanduser("~/obsidian-vault")


settings = Settings()
