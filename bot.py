"""Johnny v0.2 — Hello World.

A quiet Telegram teammate: lives in a group, stays silent by default, and replies
only when tagged or replied-to. Behavior comes from memory/johnny.md (its system
prompt) and memory/project.md (project context) — edit those in GitHub, no code
change needed. GitHub is the source of truth.

Run:  python bot.py   (needs TELEGRAM_BOT_TOKEN and ANTHROPIC_API_KEY — see .env.example)
"""

import logging
import os
from pathlib import Path

import anthropic
from telegram import Update

try:
    from dotenv import load_dotenv

    load_dotenv()  # load TELEGRAM_BOT_TOKEN / ANTHROPIC_API_KEY from a local .env
except ImportError:
    pass
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("johnny")

MEMORY_DIR = Path(__file__).parent / "memory"
MODEL = os.environ.get("JOHNNY_MODEL", "claude-opus-5")
MAX_TOKENS = int(os.environ.get("JOHNNY_MAX_TOKENS", "1024"))

# Optional whitelist: comma-separated Telegram user IDs. If set, Johnny only
# answers these users. Empty = answer anyone in the group (fine for v0.2).
_allowed = os.environ.get("JOHNNY_ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS = {int(x) for x in _allowed.split(",") if x.strip()} if _allowed else set()

claude = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def build_system_prompt() -> str:
    """Assemble Johnny's system prompt from the versioned memory files."""
    parts = []
    for name in ("johnny.md", "project.md"):
        path = MEMORY_DIR / name
        if path.exists():
            parts.append(f"# From memory/{name}\n\n{path.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(parts)


def is_directed_at_johnny(update: Update, bot_username: str) -> bool:
    """True only when the message tags Johnny (@bot) or replies to one of his messages."""
    msg = update.effective_message
    if msg is None or not msg.text:
        return False
    if f"@{bot_username}".lower() in msg.text.lower():
        return True
    if (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.username
        and msg.reply_to_message.from_user.username.lower() == bot_username.lower()
    ):
        return True
    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_username = context.bot.username
    if not is_directed_at_johnny(update, bot_username):
        return  # stay silent by default

    user = update.effective_user
    if ALLOWED_USER_IDS and (user is None or user.id not in ALLOWED_USER_IDS):
        log.info("Ignoring non-whitelisted user %s", user.id if user else "?")
        return

    text = update.effective_message.text.replace(f"@{bot_username}", "").strip()
    log.info("Answering %s: %s", user.username if user else "?", text[:80])

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    try:
        response = claude.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=build_system_prompt(),
            output_config={"effort": "low"},  # concise, low-latency replies
            messages=[{"role": "user", "content": text}],
        )
        reply = next(
            (b.text for b in response.content if b.type == "text"), ""
        ).strip() or "(no reply)"
    except Exception:
        log.exception("Claude call failed")
        reply = "Sorry — something went wrong reaching my brain. Try again in a moment."

    await update.effective_message.reply_text(reply)


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Johnny is up. Model=%s. Whitelist=%s", MODEL, ALLOWED_USER_IDS or "off")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
