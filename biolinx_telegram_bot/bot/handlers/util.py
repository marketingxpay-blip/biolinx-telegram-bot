"""Setup helpers so no terminal is ever needed to go live.

  /id         -> in any chat, the bot replies with that chat's id + thread id.
                 Use it to grab the supergroup id (type /id@YourBotUsername).
  forward     -> forward any post from the Home channel to the bot in a DM;
                 the bot replies with that channel's id.

Both exist purely to discover the IDs that go into Railway variables, without
running any script.
"""
import logging

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

log = logging.getLogger("util")


async def cmd_id(message: Message):
    chat = message.chat
    thread = message.message_thread_id
    await message.reply(
        f"chat id: {chat.id}\n"
        f"type: {chat.type}\n"
        f"title: {chat.title or '-'}\n"
        f"topic thread id: {thread if thread else '(none / General)'}"
    )


async def on_forwarded_dm(message: Message):
    """In a private chat, report the origin chat id of a forwarded message."""
    origin = message.forward_origin
    origin_chat = getattr(origin, "chat", None)
    if origin_chat is not None:
        await message.reply(
            f"That message came from:\n"
            f"chat id: {origin_chat.id}\n"
            f"type: {origin_chat.type}\n"
            f"title: {getattr(origin_chat, 'title', '-')}\n\n"
            f"If this is your Home channel, put that id in "
            f"BIOLINX_HOME_CHANNEL_ID."
        )
    else:
        await message.reply(
            "Forward a post from your Home channel here and I'll give you its id."
        )


async def cmd_testpost(message: Message):
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("creator", "administrator"):
            return
    except Exception:
        return
    from ..scheduler import post_daily_poll, post_daily_qotd
    await post_daily_poll(message.bot)
    await post_daily_qotd(message.bot)
    await message.reply("Posted a poll + Question of the Day in Bio-Lounge for testing.")


async def cmd_cleanup(message: Message):
    """Admin-only: delete every forum topic except the bot's own current set + General."""
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ("creator", "administrator"):
            return
    except Exception:
        return
    from .. import db
    keep = set()
    for key in ("pf_topic_id", "games_topic_id", "lounge_topic_id", "questions_topic_id"):
        v = db.kv_get(key)
        if v:
            keep.add(int(v))
    deleted = 0
    for tid in range(2, 80):
        if tid in keep:
            continue
        try:
            ok = await message.bot.delete_forum_topic(message.chat.id, tid)
            if ok:
                deleted += 1
        except Exception:
            pass
    await message.reply(f"Cleanup done. Deleted {deleted} old topics. Kept {len(keep)} + General.")


def register(dp: Dispatcher):
    dp.message.register(cmd_testpost, Command("testpost"))
    dp.message.register(cmd_cleanup, Command("cleanup"))
    dp.message.register(cmd_id, Command("id"))
    # Private-chat forwarded messages only.
    dp.message.register(on_forwarded_dm,
                        F.chat.type == "private",
                        F.forward_origin)
