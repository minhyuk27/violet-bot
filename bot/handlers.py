"""봇 핸들러."""
import asyncio
import logging
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes
from config.settings import settings
from agent.violet_agent import ask_claude
from agent.session_store import session_store
from agent import cost_tracker

logger = logging.getLogger(__name__)

# 사용자별 동시 요청 제한
_user_locks: dict[int, asyncio.Lock] = {}


def _get_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


def _is_allowed(user_id: int) -> bool:
    if not settings.ALLOWED_USER_IDS:
        logger.warning("ALLOWED_USER_IDS 미설정 — 모든 접근 거부")
        return False
    return user_id in settings.ALLOWED_USER_IDS


def _split(text: str, limit: int = 4096) -> list[str]:
    """단락 경계를 우선해 분할."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        cut = text.rfind("\n\n", 0, limit)
        if cut == -1:
            cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return chunks


async def _edit_or_send(placeholder, update: Update, text: str) -> None:
    """placeholder를 삭제하고 새 메시지로 전송해 알림이 오도록 한다."""
    chunks = _split(text)
    try:
        await placeholder.delete()
    except Exception:
        pass
    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(chunk)


async def _typing_loop(chat) -> None:
    """Telegram typing 표시는 ~5초 후 자동 소멸. 4초마다 갱신해 유지."""
    while True:
        await chat.send_action(ChatAction.TYPING)
        await asyncio.sleep(4)


async def _run_claude(update: Update, prompt: str) -> None:
    """공통 Claude 호출 흐름: 즉시 ⏳ 표시 → 완료 시 응답으로 교체."""
    user = update.effective_user
    lock = _get_lock(user.id)

    if lock.locked():
        await update.message.reply_text("처리 중입니다. 잠시 후 다시 시도해주세요.")
        return

    async with lock:
        placeholder = await update.message.reply_text("⏳ 처리 중...")
        typing_task = asyncio.create_task(_typing_loop(update.message.chat))
        try:
            reply = await ask_claude(prompt, user.id)
        finally:
            typing_task.cancel()
        await _edit_or_send(placeholder, update, reply)


# ── 커맨드 핸들러 ──────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "violet bot 준비됐습니다.\n"
        "/new — 대화 맥락 초기화\n"
        "/inbox — Inbox 일괄 정리\n"
        "/cost — 이번 달 비용 확인"
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update.effective_user.id):
        return
    session_store.clear(update.effective_user.id)
    await update.message.reply_text("대화 맥락을 초기화했습니다. 새 대화를 시작합니다.")


async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update.effective_user.id):
        return
    await _run_claude(
        update,
        "0 System/_Inbox/ 폴더를 확인하고 쌓인 항목들을 violet 규칙에 따라 정리해줘.",
    )


async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(f"월별 누적 비용:\n{cost_tracker.summary()}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_allowed(user.id):
        logger.info("미허가 user_id=%s — 무시", user.id)
        return
    await _run_claude(update, update.message.text)
