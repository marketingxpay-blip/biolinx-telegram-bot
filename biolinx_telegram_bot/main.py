"""Biolinx Affiliate Telegram bot — entry point (long-polling).

Start locally:   python main.py
On Railway:      startCommand = "python main.py"  (worker, no public URL)

Long-polling is used deliberately (dev ref section 10): simplest, no webhook
or public HTTPS endpoint needed at this scale.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot import config, db
from bot.handlers import register_all
from bot.scheduler import build_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("main")

# Updates we need beyond the defaults: message_reaction (Bio-Lounge reaction
# points) and poll_answer (daily poll points).
ALLOWED_UPDATES = [
    "message", "edited_message", "callback_query", "poll_answer",
    "message_reaction", "message_reaction_count", "my_chat_member",
    "chat_member",
]


async def main():
    token = config.require_bot_token()
    db.init_db()

    bot = Bot(token)
    dp = Dispatcher()
    register_all(dp)

    # Self-setup on boot: once GROUP_ID is set, create topics + post pins
    # automatically. No terminal command needed. Idempotent.
    from bot.setup_group import ensure_setup
    try:
        await ensure_setup(bot)
    except Exception as e:
        log.warning("ensure_setup on boot failed (will retry next boot): %s", e)

    sched = build_scheduler(bot)
    sched.start()
    # Kick a leaderboard refresh shortly after boot.
    from bot.handlers.games import refresh_leaderboard
    asyncio.create_task(_delayed(refresh_leaderboard, bot, delay=5))

    me = await bot.get_me()
    log.info("Starting @%s (id %s). Long-polling.", me.username, me.id)
    try:
        await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    finally:
        sched.shutdown(wait=False)
        await bot.session.close()


async def _delayed(fn, *args, delay=5):
    await asyncio.sleep(delay)
    try:
        await fn(*args)
    except Exception as e:
        log.warning("startup task %s failed: %s", fn.__name__, e)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down.")
