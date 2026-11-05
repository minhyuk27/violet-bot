"""Claude 에이전트 래퍼.

- cwd=VAULT_DIR, 읽기·쓰기·Bash(안전 게이트) 전체 활성.
- 세션 재개: 30분 비활성 전까지 대화 맥락 유지.
- 타임아웃: 5분 초과 시 안내 메시지 반환.
- 비용: 호출마다 cost_tracker에 누적.
"""
import re
import asyncio
import logging
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import (
    ResultMessage,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
from config.settings import settings
from agent.session_store import session_store
from agent import cost_tracker

logger = logging.getLogger(__name__)

_AUTO_TOOLS = ["Read", "Glob", "WebSearch", "WebFetch", "Edit", "Write"]
_ALL_TOOLS = _AUTO_TOOLS + ["Bash"]

_BLOCK_PATTERNS = [
    r"\brm\b.*\s-[^\s]*[rR]",
    r"\brm\b.*--recursive",
    r"\bfind\b.*-delete\b",
    r"\bfind\b.*-exec\s+rm\b",
    r"\bfind\b.*\|\s*xargs\b.*\brm\b",
    r"\bshred\b",
    r"\bdd\b.*\bof=/dev/",
    r"\bmkfs\b",
    r"\bfdisk\b",
    r"\bparted\b",
    r">\s*/etc/",
    r">\s*/boot/",
]


async def _can_use_bash(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    cmd = tool_input.get("command", "")
    for pattern in _BLOCK_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            logger.warning("Bash 차단 | cmd=%r", cmd[:120])
            return PermissionResultDeny(message=f"위험한 명령으로 차단됩니다: {cmd[:80]}")
    logger.info("Bash 허용 | cmd=%r", cmd[:120])
    return PermissionResultAllow()


async def _prompt_stream(text: str):
    """can_use_tool 사용 시 SDK가 요구하는 AsyncIterable 형식으로 변환."""
    yield {"type": "user", "message": {"role": "user", "content": text}}


async def ask_claude(prompt: str, user_id: int) -> str:
    session_id = session_store.get(user_id)

    opts = ClaudeAgentOptions(
        cwd=settings.VAULT_DIR,
        tools=_ALL_TOOLS,
        allowed_tools=_AUTO_TOOLS,
        disallowed_tools=["Agent"],
        can_use_tool=_can_use_bash,
        max_turns=15,
        resume=session_id,
    )

    async def _run():
        async for msg in query(prompt=_prompt_stream(prompt), options=opts):
            if isinstance(msg, ResultMessage):
                if msg.session_id:
                    session_store.update(user_id, msg.session_id)
                cost_tracker.add(msg.total_cost_usd or 0)
                if msg.is_error:
                    logger.error("Claude 오류: %s | session=%s", msg.result, session_id)
                    session_store.clear(user_id)
                    return f"오류가 발생했습니다: {msg.result}"
                logger.info(
                    "응답 완료 | cost=$%.4f turns=%d session=%s",
                    msg.total_cost_usd or 0,
                    msg.num_turns,
                    msg.session_id,
                )
                return msg.result or "(응답 없음)"
        return "(응답 없음)"

    try:
        return await asyncio.wait_for(_run(), timeout=300)
    except asyncio.TimeoutError:
        logger.warning("타임아웃 | user_id=%s", user_id)
        return "응답 시간이 초과됐습니다 (5분). 질문을 더 짧게 나눠 시도해주세요."
