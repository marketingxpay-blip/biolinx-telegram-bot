"""One-time group setup: create the 4 forum topics, post + pin all copy.

Run ONCE after the supergroup exists and the bot is an admin:

    python -m bot.setup_group

Prereqs (done by Jakob in the Telegram app — see README section 3):
  - Supergroup created with Topics ENABLED.
  - Bot added as an admin with "Manage Topics" + "Pin Messages" rights.
  - A broadcast Channel created for Home, bot added as admin there too.
  - BIOLINX_GROUP_ID and BIOLINX_HOME_CHANNEL_ID set in .env.

Idempotent: topic IDs are cached in kv; re-running won't duplicate topics.

Helper:
    python -m bot.setup_group --show-chat-id
prints updates so you can read the group/channel IDs, then exits.
"""
import asyncio
import logging
import sys

from aiogram import Bot

from . import config, db
from .copy import (HOME_PIN, pass_or_flag_pin, BIO_LOUNGE_PIN,
                   GOT_QUESTIONS_PIN)
from .handlers.games import refresh_leaderboard

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("setup")

TOPICS = [
    # (kv_key, title, icon_color)
    ("pf_topic_id", "🎮 Pass or Flag", 0x6FB9F0),
    ("games_topic_id", "🏆 The Biolinx Games", 0xFFD67E),
    ("lounge_topic_id", "🛋️ Bio-Lounge", 0xCB86DB),
    ("questions_topic_id", "❓ Got Questions", 0xFB6F5F),
]


async def _create_topics(bot: Bot, group_id: int):
    for key, title, color in TOPICS:
        if db.kv_get(key):
            log.info("Topic %s already exists (%s) — skipping", title,
                     db.kv_get(key))
            continue
        try:
            t = await bot.create_forum_topic(chat_id=group_id, name=title,
                                             icon_color=color)
            db.kv_set(key, t.message_thread_id)
            log.info("Created topic %s -> thread %s", title,
                     t.message_thread_id)
        except Exception as e:
            log.error("Could not create topic %s: %s", title, e)


async def _post_and_pin(bot, group_id, topic_key, text, pin_kv=None):
    topic_id = db.kv_get(topic_key)
    kwargs = {"chat_id": group_id, "text": text}
    if topic_id:
        kwargs["message_thread_id"] = int(topic_id)
    msg = await bot.send_message(**kwargs)
    if pin_kv:
        db.kv_set(pin_kv, msg.message_id)
    try:
        await bot.pin_chat_message(group_id, msg.message_id,
                                   disable_notification=True)
    except Exception as e:
        log.warning("pin failed in %s: %s", topic_key, e)
    return msg.message_id


async def ensure_setup(bot: Bot) -> bool:
    """Idempotent group setup, safe to call on every boot.

    Runs once: creates the 4 topics, posts + pins all copy, registers
    commands. Only flags 'setup_done' when ALL 4 topics were created, so a
    transient failure (bot not yet admin, topics disabled) retries next boot
    instead of silently marking itself done.

    Returns True if setup is complete (either just finished or already done).
    """
    if not config.GROUP_ID:
        log.info("No BIOLINX_GROUP_ID yet — bot is up, waiting for the id. "
                 "Type /id in the group to grab it.")
        return False
    if db.kv_get("setup_done") == "1":
        return True

    db.kv_set("group_id", config.GROUP_ID)
    if config.HOME_CHANNEL_ID:
        db.kv_set("home_channel_id", config.HOME_CHANNEL_ID)

    # 1. Home channel pin.
    if config.HOME_CHANNEL_ID:
        try:
            m = await bot.send_message(config.HOME_CHANNEL_ID, HOME_PIN)
            await bot.pin_chat_message(config.HOME_CHANNEL_ID, m.message_id,
                                       disable_notification=True)
            log.info("Posted + pinned Home channel guide.")
        except Exception as e:
            log.error("Home channel post failed: %s", e)
    else:
        log.warning("No HOME_CHANNEL_ID — skipping Home pin.")

    # 2. Forum topics.
    await _create_topics(bot, config.GROUP_ID)

    # 3. Topic pins.
    await _post_and_pin(bot, config.GROUP_ID, "pf_topic_id", pass_or_flag_pin())
    await _post_and_pin(bot, config.GROUP_ID, "lounge_topic_id", BIO_LOUNGE_PIN)
    await _post_and_pin(bot, config.GROUP_ID, "questions_topic_id",
                        GOT_QUESTIONS_PIN)

    # 4. Games leaderboard (creates + pins its own message).
    await refresh_leaderboard(bot)

    # 5. Register the command list shown in the Telegram UI.
    from aiogram.types import BotCommand
    try:
        await bot.set_my_commands([
            BotCommand(command="play", description="Start a Pass or Flag round"),
            BotCommand(command="faq", description="Show the FAQ buttons"),
        ])
    except Exception as e:
        log.warning("set_my_commands failed: %s", e)

    all_topics_made = all(
        db.kv_get(key) for key, _, _ in TOPICS)
    if all_topics_made:
        db.kv_set("setup_done", "1")
        log.info("Setup complete. Topics + pins posted, flagged done.")
        return True
    log.warning("Setup incomplete (topics missing — is the bot an admin with "
                "Manage Topics, and are Topics enabled?). Will retry next boot.")
    return False


async def run_setup():
    """CLI entry: build a bot and run ensure_setup once."""
    db.init_db()
    bot = Bot(config.require_bot_token())
    if not config.GROUP_ID:
        log.error("BIOLINX_GROUP_ID not set. Run --show-chat-id to find it.")
        await bot.session.close()
        return
    await ensure_setup(bot)
    await bot.session.close()


async def show_chat_id():
    """Print incoming updates' chat IDs, so you can grab the group/channel ID."""
    from aiogram import Dispatcher
    from aiogram.types import Message
    bot = Bot(config.require_bot_token())
    dp = Dispatcher()

    @dp.message()
    async def _echo(m: Message):
        print(f"chat_id={m.chat.id}  type={m.chat.type}  "
              f"title={m.chat.title!r}  thread={m.message_thread_id}")

    print("Post any message in the group/channel (or add the bot). Ctrl-C to stop.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    if "--show-chat-id" in sys.argv:
        asyncio.run(show_chat_id())
    else:
        asyncio.run(run_setup())
