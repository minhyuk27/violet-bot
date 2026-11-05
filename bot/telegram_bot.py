"""violet Telegram Bot."""
import asyncio
import glob
import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.handlers import cmd_start, cmd_new, cmd_inbox, cmd_cost, handle_message
from config.settings import settings

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _check_conflicts(app: Application) -> None:
    """Syncthing 충돌 파일 발견 시 허가 사용자에게 알림."""
    pattern = os.path.join(settings.VAULT_DIR, "**", "*.sync-conflict-*.md")
    conflicts = glob.glob(pattern, recursive=True)
    if not conflicts:
        return
    rel = [os.path.relpath(c, settings.VAULT_DIR) for c in conflicts[:10]]
    extra = f" 외 {len(conflicts) - 10}개" if len(conflicts) > 10 else ""
    text = (
        f"Syncthing 충돌 파일 발견 ({len(conflicts)}개{extra}):\n"
        + "\n".join(f"- {r}" for r in rel)
    )
    for uid in settings.ALLOWED_USER_IDS:
        try:
            await app.bot.send_message(chat_id=uid, text=text)
        except Exception as e:
            logger.error("충돌 알림 전송 실패 uid=%s: %s", uid, e)


async def _conflict_loop(app: Application) -> None:
    await asyncio.sleep(60)  # 시작 후 1분 뒤 첫 검사
    while True:
        try:
            await _check_conflicts(app)
        except Exception as e:
            logger.error("충돌 검사 오류: %s", e)
        await asyncio.sleep(1800)  # 30분마다


async def _post_init(app: Application) -> None:
    if settings.ALLOWED_USER_IDS:
        asyncio.create_task(_conflict_loop(app))


def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(".env에 TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")

    logger.info("violet bot 시작")
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("new",    cmd_new))
    app.add_handler(CommandHandler("inbox",  cmd_inbox))
    app.add_handler(CommandHandler("cost",   cmd_cost))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("폴링 시작...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
