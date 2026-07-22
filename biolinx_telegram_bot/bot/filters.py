"""Runtime topic filters.

Topic thread IDs are only known after setup_group runs (stored in the kv
table). These filters read kv at call time so routing follows whatever the
current group layout is. Before setup, they simply don't match — safe.
"""
from aiogram.types import Message

from . import db


def in_topic(topic_key: str):
    """Return an aiogram filter matching messages in the given topic."""
    async def _filter(message: Message) -> bool:
        tid = db.kv_get(topic_key)
        if not tid:
            return False
        # General topic has thread id 1 / None; our tabs are real topics.
        return str(message.message_thread_id) == str(tid)
    return _filter
