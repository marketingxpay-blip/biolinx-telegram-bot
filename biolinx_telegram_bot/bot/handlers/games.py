"""The Biolinx Games — pinned leaderboard, auto-refreshed on a timer.

Read-only tab. The bot keeps ONE pinned message updated in place
(editMessageText) rather than spamming new posts. Data comes from
raza_feed (dummy until Raza's endpoint lands).
"""
import calendar
import datetime as dt
import logging

from .. import db, raza_feed
from ..copy import games_pin

log = logging.getLogger("games")


def _days_left_this_month() -> int:
    today = dt.datetime.utcnow()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return max(last_day - today.day, 0)


async def refresh_leaderboard(bot):
    """Rebuild and edit the pinned Games message. Safe to call on a timer."""
    group_id = db.kv_get("group_id")
    games_topic = db.kv_get("games_topic_id")
    pin_msg_id = db.kv_get("games_pin_msg_id")
    if not group_id:
        log.info("No group_id yet; skipping leaderboard refresh.")
        return

    rows, is_live = await raza_feed.get_leaderboard()
    text = games_pin(_days_left_this_month(), rows[:3])
    if not is_live:
        text += "\n\n(sample data — live standings begin once the feed is connected)"

    try:
        if pin_msg_id:
            await bot.edit_message_text(
                text=text, chat_id=int(group_id), message_id=int(pin_msg_id))
        else:
            kwargs = {"chat_id": int(group_id), "text": text}
            if games_topic:
                kwargs["message_thread_id"] = int(games_topic)
            msg = await bot.send_message(**kwargs)
            db.kv_set("games_pin_msg_id", msg.message_id)
            try:
                await bot.pin_chat_message(int(group_id), msg.message_id,
                                           disable_notification=True)
            except Exception as e:
                log.warning("pin failed: %s", e)
    except Exception as e:
        # Telegram raises if the text is identical ("message is not modified").
        if "not modified" not in str(e).lower():
            log.warning("leaderboard refresh failed: %s", e)
