"""Pass or Flag — /play, ephemeral rounds, scoring, entries, badges.

Flow (dev ref section 4):
  1. Member types /play in the Pass or Flag topic.
  2. Bot sends the round as an EPHEMERAL message (visible only to that member)
     with ✅ / 🚩 inline buttons.
  3. Member taps -> callback_query -> bot locks the answer (first tap only),
     edits the ephemeral message with the result, advances to the next
     caption. answerCallbackQuery is always called.
  4. After 10, bot shows the summary and records the session (entries/badge).

Anti-gaming: 3 tries/day, up to 3 entries/day, first-tap lock, per-member
randomized order, UTC reset (all enforced in db.py + game.py).
"""
import asyncio
import logging
import random

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .. import db, game, config
from ..copy import (round_caption_prompt, reply_correct, reply_wrong)
from .. import ephemeral

log = logging.getLogger("pass_or_flag")

# Runtime state: telegram_user_id -> session dict.
ACTIVE = {}


def _keyboard():
    return {"inline_keyboard": [[
        {"text": "✅ compliant", "callback_data": "pf_PASS"},
        {"text": "🚩 not compliant", "callback_data": "pf_FLAG"},
    ]]}


def _finished_markup():
    return {"inline_keyboard": []}


async def _send_round_body(chat_id, user_id, thread_id, rnd, prefix=""):
    """Send/refresh the ephemeral round message. Returns eph id or None."""
    text = prefix + round_caption_prompt(rnd.current_caption[0])
    return await ephemeral.send_ephemeral(
        chat_id=chat_id, receiver_user_id=user_id, text=text,
        message_thread_id=thread_id, reply_markup=_keyboard())


async def cmd_play(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id

    # Only valid in the Pass or Flag topic (if configured).
    pf_topic = db.kv_get("pf_topic_id")
    if pf_topic and thread_id and str(thread_id) != str(pf_topic):
        return  # ignore /play outside its tab

    await asyncio.to_thread(db.upsert_affiliate, user_id,
                            name=message.from_user.full_name)
    aff = await asyncio.to_thread(db.get_affiliate_id, user_id)

    allowed, reason = await asyncio.to_thread(db.can_play, aff)
    if not allowed:
        await ephemeral.send_ephemeral(chat_id, user_id, reason, thread_id)
        return

    rnd = game.new_round(random.Random())
    eph_id = await _send_round_body(chat_id, user_id, thread_id, rnd)
    if eph_id is None:
        # Ephemeral send failed -> fall back to a private DM so the member
        # can still play (never a dead end).
        try:
            await message.bot.send_message(
                user_id,
                "Your Pass or Flag round (private):\n\n"
                + round_caption_prompt(rnd.current_caption[0]),
                reply_markup=_dm_keyboard())
        except Exception:
            await message.reply("Start a chat with me first, then /play again.")
            return
    ACTIVE[user_id] = {"round": rnd, "chat_id": chat_id,
                       "thread": thread_id, "eph_id": eph_id, "aff": aff}


def _dm_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ compliant", callback_data="pf_PASS"),
        InlineKeyboardButton(text="🚩 not compliant", callback_data="pf_FLAG"),
    ]])


async def on_answer(cq: CallbackQuery):
    user_id = cq.from_user.id
    sess = ACTIVE.get(user_id)
    if not sess:
        await cq.answer("This round expired. Type /play to start a new one.",
                        show_alert=True)
        return

    choice = "PASS" if cq.data == "pf_PASS" else "FLAG"
    rnd = sess["round"]
    try:
        res = game.answer(rnd, choice)
    except ValueError:
        await cq.answer()  # already answered / finished; stop the spinner
        return

    await cq.answer()  # REQUIRED on every callback

    # Build the result line + streak callout.
    line = (reply_correct(res["reason"], res["score"], res["answered"])
            if res["correct"]
            else reply_wrong(res["reason"], res["score"], res["answered"]))
    if res["streak_callout"]:
        line += f"\n{res['streak_callout']}"

    if res["finished"]:
        await _finish(cq, sess, rnd)
        return

    # Show result briefly, then the next caption in the same ephemeral msg.
    next_text = line + "\n\n" + round_caption_prompt(rnd.current_caption[0])
    await _edit(cq, sess, next_text, _keyboard())


async def _finish(cq, sess, rnd):
    aff = sess["aff"]
    entries, badge = await asyncio.to_thread(
        db.record_session, aff, cq.from_user.id, rnd.score)

    summary = f"Round over. Score: {rnd.score}/{config.ROUND_SIZE}\n"
    if badge:
        summary += "\nPerfect. You earned this month's Bio Badge (200 pts)."
    elif entries:
        summary += "\nYou scored 7+. That's 1 free giveaway entry this month."
    elif rnd.score >= config.PASS_THRESHOLD:
        summary += ("\nYou scored 7+, but you've hit today's 3-entry cap. "
                    "Nice round though.")
    else:
        summary += "\nScore 7 of 10 next time to earn a free entry. 3 tries a day."

    tries_left = config.MAX_TRIES_PER_DAY - await asyncio.to_thread(
        db.tries_today, aff)
    if tries_left > 0:
        summary += f"\n\n/play again — {tries_left} tries left today."

    await _edit(cq, sess, summary, _finished_markup())
    ACTIVE.pop(cq.from_user.id, None)


async def _edit(cq, sess, text, markup):
    """Edit the ephemeral round message; DM fallback if it was a DM round."""
    if sess.get("eph_id"):
        await ephemeral.edit_ephemeral_text(
            sess["chat_id"], sess["eph_id"], text, reply_markup=markup)
    else:
        try:
            await cq.message.edit_text(
                text,
                reply_markup=(_dm_keyboard() if markup.get("inline_keyboard")
                              else None))
        except Exception as e:
            log.warning("edit fallback failed: %s", e)


def register(dp: Dispatcher):
    dp.message.register(cmd_play, Command("play"))
    dp.callback_query.register(on_answer, F.data.in_({"pf_PASS", "pf_FLAG"}))
