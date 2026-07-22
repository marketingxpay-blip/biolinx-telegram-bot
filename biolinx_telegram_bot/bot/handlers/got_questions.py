"""Got Questions — tappable FAQ buttons + grounded AI answers + admin log.

Requires BotFather privacy mode = Disabled so the bot sees all messages in
this topic. Answers are sent EPHEMERAL (private to the asker), signed Lincoln.
Misses are logged to faq_log and admins are pinged.
"""
import asyncio
import logging

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from .. import db, config, ephemeral, faq_ai
from ..filters import in_topic
from ..copy import FAQ_BUTTONS, FAQ_ANSWERS, FAQ_SIGNATURE, FAQ_FALLBACK

log = logging.getLogger("got_questions")


def _faq_keyboard():
    rows = [[{"text": q, "callback_data": f"faq_{i}"}]
            for i, q in enumerate(FAQ_BUTTONS)]
    return {"inline_keyboard": rows}


async def cmd_faq(message: Message):
    """Post the tappable FAQ buttons into the Got Questions topic."""
    await ephemeral.send_ephemeral(
        message.chat.id, message.from_user.id,
        "Tap a question:", message.message_thread_id,
        reply_markup=_faq_keyboard())


async def on_faq_button(cq: CallbackQuery):
    idx = int(cq.data.split("_", 1)[1])
    question = FAQ_BUTTONS[idx]
    answer = FAQ_ANSWERS.get(question)
    await cq.answer()
    if answer:
        reply = f"{answer}\n\n{FAQ_SIGNATURE}"
        answered = True
    else:
        reply = f"{FAQ_FALLBACK}\n\n{FAQ_SIGNATURE}"
        answered = False
    await ephemeral.send_ephemeral(
        cq.message.chat.id, cq.from_user.id, reply,
        cq.message.message_thread_id)
    await asyncio.to_thread(db.log_faq, question, cq.from_user.id,
                            answered, answer)
    if not answered:
        await _ping_admins(cq.bot, question, cq.from_user)


async def on_question(message: Message):
    """Free-text question in the Got Questions topic -> grounded AI answer."""
    text = (message.text or "").strip()
    if len(text) < 4:
        return

    reply, answered = await faq_ai.answer_question(text)
    await ephemeral.send_ephemeral(
        message.chat.id, message.from_user.id, reply,
        message.message_thread_id)
    await asyncio.to_thread(db.log_faq, text, message.from_user.id,
                            answered, reply if answered else None)
    if not answered:
        await _ping_admins(message.bot, text, message.from_user)


async def _ping_admins(bot, question, user):
    note = (f"New unanswered question logged.\n\nFrom: {user.full_name} "
            f"(id {user.id})\nQ: {question}")
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, note)
        except Exception as e:
            log.warning("admin ping failed for %s: %s", admin_id, e)


def register(dp: Dispatcher):
    dp.message.register(cmd_faq, Command("faq"))
    dp.callback_query.register(on_faq_button, F.data.startswith("faq_"))
    # Free-text questions: only inside the Got Questions topic.
    dp.message.register(on_question,
                        in_topic("questions_topic_id"),
                        F.text & ~F.text.startswith("/"))
