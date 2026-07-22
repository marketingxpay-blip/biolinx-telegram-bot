"""Central config. Loads .env and exposes typed settings.

Nothing here fails at import time except a missing bot token when actually
starting the bot — so the test suite and the caption/copy modules import
cleanly without any secrets present.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default=None):
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _int_list(name: str):
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                out.append(int(part))
            except ValueError:
                pass
    return out


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GROUP_ID = _int("BIOLINX_GROUP_ID")
HOME_CHANNEL_ID = _int("BIOLINX_HOME_CHANNEL_ID")
ADMIN_IDS = _int_list("BIOLINX_ADMIN_IDS")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip()

RAZA_FEED_URL = os.getenv("RAZA_FEED_URL", "").strip()
RAZA_FEED_KEY = os.getenv("RAZA_FEED_KEY", "").strip()

DB_PATH = os.getenv("DB_PATH", "biolinx.db").strip()

DAILY_POLL_UTC_HOUR = _int("DAILY_POLL_UTC_HOUR", 15)
DAILY_QOTD_UTC_HOUR = _int("DAILY_QOTD_UTC_HOUR", 17)
LEADERBOARD_REFRESH_MINUTES = _int("LEADERBOARD_REFRESH_MINUTES", 60)

# Points economy (locked in build doc section 5).
PTS_POLL = 1
PTS_QOTD = 1
PTS_REPLY = 2
PTS_REACTIONS = 3
MONTHLY_CREDIT_CAP_PTS = 150      # 150 pts/month max toward store credit
PTS_PER_DOLLAR_BLOCK = 100         # 100 pts = $5
BADGE_PTS = 200                    # Bio Badge award, uncapped bucket

# Pass or Flag rules (locked in build doc section 5).
ROUND_SIZE = 10
PASS_THRESHOLD = 7                 # 7/10 = 1 giveaway entry
PERFECT_SCORE = 10                 # 10/10 = Bio Badge
MAX_TRIES_PER_DAY = 3
MAX_ENTRIES_PER_DAY = 3


def require_bot_token() -> str:
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Add it to .env (local) or to the "
            "Railway service Variables, then restart. See README section 2."
        )
    return BOT_TOKEN
