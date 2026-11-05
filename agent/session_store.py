"""사용자별 Claude 세션 ID 관리. 30분 비활성 시 자동 만료."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

SESSION_TIMEOUT = timedelta(minutes=30)


@dataclass
class _Session:
    session_id: str
    last_active: datetime = field(default_factory=datetime.utcnow)


class SessionStore:
    def __init__(self):
        self._store: dict[int, _Session] = {}

    def get(self, user_id: int) -> str | None:
        s = self._store.get(user_id)
        if s is None:
            return None
        if datetime.utcnow() - s.last_active > SESSION_TIMEOUT:
            del self._store[user_id]
            return None
        return s.session_id

    def update(self, user_id: int, session_id: str) -> None:
        self._store[user_id] = _Session(session_id=session_id)

    def clear(self, user_id: int) -> None:
        self._store.pop(user_id, None)


session_store = SessionStore()
