"""APScheduler jobs — daily poll, Question of the Day, leaderboard refresh.

Runs in the same asyncio loop as aiogram (why aiogram was chosen). All times
are UTC (anti clock-gaming rule). Poll and QotD rotate through their banks;
the current index persists in kv so rotation survives restarts.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import db, config
from .copy import POLL_BANK, QOTD_BANK
from .handlers.games import refresh_leaderboard

log = logging.getLogger("scheduler")


def _next_index(key, length) -> int:
    cur = int(db.kv_get(key, "0"))
    db.kv_set(key, (cur + 1) % length)
    return cur % length


async def post_daily_poll(bot):
    group_id = db.kv_get("group_id")
    lounge = db.kv_get("lounge_topic_id")
    if not group_id:
        return
    q, opts = POLL_BANK[_next_index("poll_idx", len(POLL_BANK))]
    kwargs = {"chat_id": int(group_id), "question": q, "options": opts,
              "is_anonymous": False}
    if lounge:
        kwargs["message_thread_id"] = int(lounge)
    try:
        await bot.send_poll(**kwargs)
        log.info("Posted daily poll: %s", q)
    except Exception as e:
        log.warning("daily poll failed: %s", e)


async def post_daily_qotd(bot):
    group_id = db.kv_get("group_id")
    lounge = db.kv_get("lounge_topic_id")
    if not group_id:
        return
    q = QOTD_BANK[_next_index("qotd_idx", len(QOTD_BANK))]
    text = f"Question of the Day\n\n{q}\n\nReply to earn 1 point."
    kwargs = {"chat_id": int(group_id), "text": text}
    if lounge:
        kwargs["message_thread_id"] = int(lounge)
    try:
        msg = await bot.send_message(**kwargs)
        db.kv_set("qotd_msg_id", msg.message_id)  # replies to this earn pts
        log.info("Posted QotD: %s", q)
    except Exception as e:
        log.warning("QotD failed: %s", e)


def build_scheduler(bot) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(post_daily_poll, "cron", hour=config.DAILY_POLL_UTC_HOUR,
                  minute=0, args=[bot], id="daily_poll")
    sched.add_job(post_daily_qotd, "cron", hour=config.DAILY_QOTD_UTC_HOUR,
                  minute=0, args=[bot], id="daily_qotd")
    sched.add_job(refresh_leaderboard, "interval",
                  minutes=config.LEADERBOARD_REFRESH_MINUTES, args=[bot],
                  id="leaderboard", next_run_time=None)
    return sched
