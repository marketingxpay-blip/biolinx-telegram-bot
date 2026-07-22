"""Raw HTTP wrappers for the Bot API 10.2 ephemeral-message methods.

Why raw HTTP: ephemeral messages shipped July 2026 (Bot API 10.2). aiogram
3.30 does not yet expose typed wrappers for editEphemeralMessageText et al.,
so we call the endpoints directly. Everything else in the bot uses aiogram.

Reference: core.telegram.org/bots/features#ephemeral-messages
Mechanism: pass receiver_user_id on a send* method to make the message
visible to exactly one group member; edit/delete it later via the
*EphemeralMessage* methods using the returned ephemeral_message_id.

Every call degrades safely: if the ephemeral send is rejected for any reason
the caller can fall back to a private DM (see pass_or_flag handler).
"""
import logging
import aiohttp

from . import config

log = logging.getLogger("ephemeral")

_API = "https://api.telegram.org/bot{token}/{method}"


async def _call(method: str, payload: dict) -> dict:
    url = _API.format(token=config.require_bot_token(), method=method)
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as r:
            data = await r.json()
    if not data.get("ok"):
        log.warning("Telegram %s failed: %s", method, data.get("description"))
    return data


async def send_ephemeral(chat_id, receiver_user_id, text,
                         message_thread_id=None, reply_markup=None,
                         callback_query_id=None):
    """Send a group message visible only to receiver_user_id.

    Returns the ephemeral_message_id on success, else None.
    """
    payload = {
        "chat_id": chat_id,
        "receiver_user_id": receiver_user_id,
        "text": text,
    }
    # General topic (thread id 1) must NOT carry message_thread_id.
    if message_thread_id and message_thread_id != 1:
        payload["message_thread_id"] = message_thread_id
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if callback_query_id is not None:
        payload["callback_query_id"] = callback_query_id
    data = await _call("sendMessage", payload)
    if data.get("ok"):
        res = data["result"]
        return res.get("ephemeral_message_id") or res.get("message_id")
    return None


async def edit_ephemeral_text(chat_id, ephemeral_message_id, text,
                              reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "ephemeral_message_id": ephemeral_message_id,
        "text": text,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await _call("editEphemeralMessageText", payload)


async def delete_ephemeral(chat_id, ephemeral_message_id):
    return await _call("deleteEphemeralMessage", {
        "chat_id": chat_id,
        "ephemeral_message_id": ephemeral_message_id,
    })
