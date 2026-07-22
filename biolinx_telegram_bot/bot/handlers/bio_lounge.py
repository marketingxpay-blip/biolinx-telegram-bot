"""Bio-Lounge — points tracking + (scheduler posts the daily poll & QotD).

Point sources (build doc 5):
  - Daily poll answer ...... 1 pt  (once/day)
  - Question of the Day .... 1 pt  (once/day, = reply to the QotD message)
  - Reply to an affiliate .. 2 pts
  - Reactions on your post . 3 pts (awarded once when a post crosses threshold)

Two counters live in db.py: capped store-credit (150/mo) and the uncapped
Bio Badge bucket. This module only feeds the lounge point columns; the cap is
applied on read.
"""
import asyncio
import logging

from aiogram import Dispatcher, F
from aiogram.types import Message, PollAnswer, MessageReactionUpdated

from .. import db, config
from ..filters import in_topic

log = logging.getLogger("bio_lounge")

REACTION_THRESHOLD = 3  # reactions needed on a post to earn the 3 pts

# message_id -> author telegram_user_id (bounded, best-effort).
_AUTHORS = {}
# message_id -> set(user_ids who reacted)
_REACTIONS = {}
_MAX_TRACK = 5000


def _remember_author(message_id, user_id):
    if len(_AUTHORS) > _MAX_TRACK:
        _AUTHORS.clear()
        _REACTIONS.clear()
    _AUTHORS[message_id] = user_id


async def on_lounge_message(message: Message):
    """Track authorship, award QotD answers and replies-to-affiliates."""
    user = message.from_user
    if user is None or user.is_bot:
        return
    _remember_author(message.message_id, user.id)

    await asyncio.to_thread(db.upsert_affiliate, user.id, name=user.full_name)
    aff = await asyncio.to_thread(db.get_affiliate_id, user.id)

    reply = message.reply_to_message
    if reply is not None:
        qotd_id = db.kv_get("qotd_msg_id")
        if qotd_id and str(reply.message_id) == str(qotd_id):
            got = await asyncio.to_thread(db.award_qotd, aff)
            if got:
                log.info("QotD point -> %s", aff)
            return
        # Reply to another affiliate (not the bot, not self).
        if reply.from_user and not reply.from_user.is_bot \
                and reply.from_user.id != user.id:
            await asyncio.to_thread(db.award_reply, aff)
            log.info("Reply point -> %s", aff)


async def on_poll_answer(poll_answer: PollAnswer):
    """Any answer to a bot poll earns the daily poll point (once/day)."""
    user = poll_answer.user
    if user is None or user.is_bot:
        return
    await asyncio.to_thread(db.upsert_affiliate, user.id, name=user.full_name)
    aff = await asyncio.to_thread(db.get_affiliate_id, user.id)
    got = await asyncio.to_thread(db.award_poll, aff)
    if got:
        log.info("Poll point -> %s", aff)


async def on_reaction(evt: MessageReactionUpdated):
    """Count reactions per post; award the author once at threshold."""
    if evt.user is None:
        return
    mid = evt.message_id
    author = _AUTHORS.get(mid)
    if author is None:
        return  # we never saw the original post; can't attribute
    reactors = _REACTIONS.setdefault(mid, set())
    if evt.new_reaction:
        reactors.add(evt.user.id)
    else:
        reactors.discard(evt.user.id)
    if len(reactors) >= REACTION_THRESHOLD:
        aff = await asyncio.to_thread(db.get_affiliate_id, author)
        got = await asyncio.to_thread(db.award_reactions, mid, aff)
        if got:
            log.info("Reaction points -> %s (post %s)", aff, mid)


def register(dp: Dispatcher):
    dp.message.register(on_lounge_message, in_topic("lounge_topic_id"), F.text)
    dp.poll_answer.register(on_poll_answer)
    dp.message_reaction.register(on_reaction)
