"""Raza data feed adapter — read-and-display ONLY.

The bot performs zero calculation on this data (deliberate, to minimize error
surface — dev ref section 8). Until Raza provides the real endpoint/format,
get_leaderboard() returns clearly-labelled dummy data and the community feed
returns None so the copy shows placeholders rather than wrong numbers.

Fallback rule (locked): on any fetch failure, return the LAST GOOD numbers,
never an error or a zero state. Last-good is cached in the kv table.
"""
import json
import logging

import aiohttp

from . import config, db

log = logging.getLogger("raza_feed")

# Dummy leaderboard used until RAZA_FEED_URL is set. Marked clearly.
DUMMY_LEADERBOARD = [
    {"name": "Sample Affiliate A", "tier": "Gold", "referral_count": 42},
    {"name": "Sample Affiliate B", "tier": "Silver", "referral_count": 31},
    {"name": "Sample Affiliate C", "tier": "Silver", "referral_count": 27},
    {"name": "Sample Affiliate D", "tier": "Bronze", "referral_count": 19},
    {"name": "Sample Affiliate E", "tier": "Bronze", "referral_count": 12},
]


def _cache_leaderboard(rows):
    db.kv_set("raza_last_good_leaderboard", json.dumps(rows))


def _last_good_leaderboard():
    raw = db.kv_get("raza_last_good_leaderboard")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return None


async def get_leaderboard():
    """Return a list of {name, tier, referral_count}, sorted desc.

    (rows, is_live) — is_live=False means dummy/last-good data.
    """
    if not config.RAZA_FEED_URL:
        return DUMMY_LEADERBOARD, False

    headers = {}
    if config.RAZA_FEED_KEY:
        headers["Authorization"] = f"Bearer {config.RAZA_FEED_KEY}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(config.RAZA_FEED_URL, headers=headers,
                             timeout=aiohttp.ClientTimeout(total=20)) as r:
                data = await r.json()
        # Expected shape: list of {name, tier, referral_count}. Adapt here
        # once Raza confirms the real format.
        rows = data.get("leaderboard", data) if isinstance(data, dict) else data
        rows = sorted(rows, key=lambda x: x.get("referral_count", 0),
                      reverse=True)
        _cache_leaderboard(rows)
        return rows, True
    except Exception as e:
        log.warning("Raza feed failed (%s); using last-good/dummy.", e)
        last = _last_good_leaderboard()
        if last:
            return last, False
        return DUMMY_LEADERBOARD, False


async def get_community_stats():
    """Return {all_time_payout, month_to_date_sales} or None if unavailable.

    PENDING Raza's community feed — returns None so monthly copy uses
    placeholders instead of invented figures.
    """
    return None
