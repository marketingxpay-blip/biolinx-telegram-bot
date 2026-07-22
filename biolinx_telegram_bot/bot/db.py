"""SQLite persistence — points, streaks, badges, entries, FAQ log.

Schema follows dev reference section 9. Synchronous sqlite3 (thread-safe via
a lock); at this scale the calls are sub-millisecond. Handlers wrap calls in
asyncio.to_thread so the event loop never blocks.

All dates/months are UTC (anti clock-gaming rule, build doc section 5).
"""
import sqlite3
import threading
import datetime as dt
from contextlib import contextmanager

from . import config

_LOCK = threading.Lock()
_CONN = None


def utc_date() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def utc_month() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m")


def _connect():
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
    return _CONN


@contextmanager
def _cursor():
    conn = _connect()
    with _LOCK:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()


def init_db():
    with _cursor() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS affiliates (
                telegram_user_id INTEGER PRIMARY KEY,
                affiliate_id     TEXT,
                tier             TEXT,
                name             TEXT
            );

            CREATE TABLE IF NOT EXISTS pass_or_flag_sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                affiliate_id   TEXT,
                telegram_user_id INTEGER,
                date           TEXT,
                score          INTEGER,
                entries_earned INTEGER,
                badge_earned   INTEGER,
                created_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS lounge_points (
                affiliate_id   TEXT,
                month          TEXT,
                poll_pts       INTEGER DEFAULT 0,
                qotd_pts       INTEGER DEFAULT 0,
                reply_pts      INTEGER DEFAULT 0,
                reaction_pts   INTEGER DEFAULT 0,
                PRIMARY KEY (affiliate_id, month)
            );

            CREATE TABLE IF NOT EXISTS badges (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                affiliate_id TEXT,
                badge_name   TEXT,
                month_earned TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_earned (
                affiliate_id TEXT,
                date         TEXT,
                kind         TEXT,
                PRIMARY KEY (affiliate_id, date, kind)
            );

            CREATE TABLE IF NOT EXISTS awarded_reactions (
                message_id   INTEGER PRIMARY KEY,
                affiliate_id TEXT
            );

            CREATE TABLE IF NOT EXISTS faq_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT,
                asker_id      INTEGER,
                timestamp     TEXT,
                answered      INTEGER DEFAULT 0,
                answer_text   TEXT
            );

            CREATE TABLE IF NOT EXISTS kv (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


# ------------------------------------------------------------- affiliates
def upsert_affiliate(telegram_user_id, affiliate_id=None, tier=None, name=None):
    """Ensure a row exists; fill affiliate_id/tier/name when known.

    Anti multi-account: entries are tied to affiliate_id, not just the
    Telegram ID. Until Raza links the two, affiliate_id defaults to the
    Telegram ID so tracking still works uniquely per person.
    """
    with _cursor() as c:
        row = c.execute(
            "SELECT telegram_user_id FROM affiliates WHERE telegram_user_id=?",
            (telegram_user_id,),
        ).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO affiliates (telegram_user_id, affiliate_id, tier, name)"
                " VALUES (?,?,?,?)",
                (telegram_user_id,
                 affiliate_id or f"tg:{telegram_user_id}", tier, name),
            )
        else:
            if affiliate_id:
                c.execute("UPDATE affiliates SET affiliate_id=? WHERE telegram_user_id=?",
                          (affiliate_id, telegram_user_id))
            if tier:
                c.execute("UPDATE affiliates SET tier=? WHERE telegram_user_id=?",
                          (tier, telegram_user_id))
            if name:
                c.execute("UPDATE affiliates SET name=? WHERE telegram_user_id=?",
                          (name, telegram_user_id))


def get_affiliate_id(telegram_user_id) -> str:
    with _cursor() as c:
        row = c.execute(
            "SELECT affiliate_id FROM affiliates WHERE telegram_user_id=?",
            (telegram_user_id,),
        ).fetchone()
        return row["affiliate_id"] if row else f"tg:{telegram_user_id}"


# ------------------------------------------------ Pass or Flag limits/log
def tries_today(affiliate_id) -> int:
    with _cursor() as c:
        row = c.execute(
            "SELECT COUNT(*) n FROM pass_or_flag_sessions "
            "WHERE affiliate_id=? AND date=?",
            (affiliate_id, utc_date()),
        ).fetchone()
        return row["n"]


def entries_today(affiliate_id) -> int:
    with _cursor() as c:
        row = c.execute(
            "SELECT COALESCE(SUM(entries_earned),0) n FROM pass_or_flag_sessions "
            "WHERE affiliate_id=? AND date=?",
            (affiliate_id, utc_date()),
        ).fetchone()
        return row["n"]


def can_play(affiliate_id):
    """Return (allowed: bool, reason: str)."""
    if tries_today(affiliate_id) >= config.MAX_TRIES_PER_DAY:
        return False, "You've used all 3 tries today. Come back tomorrow (resets at UTC midnight)."
    return True, ""


def record_session(affiliate_id, telegram_user_id, score):
    """Persist a finished round. Returns (entries_earned, badge_earned)."""
    entries = 0
    badge = 0
    if score >= config.PASS_THRESHOLD:
        # 1 entry, but respect the 3-entries/day cap.
        if entries_today(affiliate_id) < config.MAX_ENTRIES_PER_DAY:
            entries = 1
    if score >= config.PERFECT_SCORE:
        badge = 1
    with _cursor() as c:
        c.execute(
            "INSERT INTO pass_or_flag_sessions "
            "(affiliate_id, telegram_user_id, date, score, entries_earned, "
            " badge_earned, created_at) VALUES (?,?,?,?,?,?,?)",
            (affiliate_id, telegram_user_id, utc_date(), score, entries, badge,
             dt.datetime.utcnow().isoformat()),
        )
    if badge:
        _award_badge(affiliate_id)
    return entries, badge


def _award_badge(affiliate_id):
    with _cursor() as c:
        c.execute(
            "INSERT INTO badges (affiliate_id, badge_name, month_earned) "
            "VALUES (?,?,?)",
            (affiliate_id, f"{dt.datetime.utcnow().strftime('%B')} Bio Badge",
             utc_month()),
        )


def badge_count(affiliate_id) -> int:
    with _cursor() as c:
        row = c.execute("SELECT COUNT(*) n FROM badges WHERE affiliate_id=?",
                        (affiliate_id,)).fetchone()
        return row["n"]


# --------------------------------------------------- Bio-Lounge points
def _ensure_month_row(c, affiliate_id):
    c.execute(
        "INSERT OR IGNORE INTO lounge_points (affiliate_id, month) VALUES (?,?)",
        (affiliate_id, utc_month()),
    )


def _award_once_per_day(affiliate_id, kind) -> bool:
    """True if this is the first award of `kind` today (and marks it)."""
    with _cursor() as c:
        try:
            c.execute(
                "INSERT INTO daily_earned (affiliate_id, date, kind) VALUES (?,?,?)",
                (affiliate_id, utc_date(), kind),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def add_points(affiliate_id, column, amount):
    """column in {poll_pts, qotd_pts, reply_pts, reaction_pts}."""
    assert column in ("poll_pts", "qotd_pts", "reply_pts", "reaction_pts")
    with _cursor() as c:
        _ensure_month_row(c, affiliate_id)
        c.execute(
            f"UPDATE lounge_points SET {column}={column}+? "
            "WHERE affiliate_id=? AND month=?",
            (amount, affiliate_id, utc_month()),
        )


def award_poll(affiliate_id) -> bool:
    if _award_once_per_day(affiliate_id, "poll"):
        add_points(affiliate_id, "poll_pts", config.PTS_POLL)
        return True
    return False


def award_qotd(affiliate_id) -> bool:
    if _award_once_per_day(affiliate_id, "qotd"):
        add_points(affiliate_id, "qotd_pts", config.PTS_QOTD)
        return True
    return False


def award_reply(affiliate_id):
    add_points(affiliate_id, "reply_pts", config.PTS_REPLY)


def award_reactions(message_id, affiliate_id) -> bool:
    """Award reaction points once per message when it crosses threshold."""
    with _cursor() as c:
        try:
            c.execute(
                "INSERT INTO awarded_reactions (message_id, affiliate_id) VALUES (?,?)",
                (message_id, affiliate_id),
            )
        except sqlite3.IntegrityError:
            return False
    add_points(affiliate_id, "reaction_pts", config.PTS_REACTIONS)
    return True


def raw_month_points(affiliate_id, month=None) -> int:
    month = month or utc_month()
    with _cursor() as c:
        row = c.execute(
            "SELECT poll_pts+qotd_pts+reply_pts+reaction_pts t "
            "FROM lounge_points WHERE affiliate_id=? AND month=?",
            (affiliate_id, month),
        ).fetchone()
        return row["t"] if row and row["t"] is not None else 0


def credited_month_points(affiliate_id, month=None) -> int:
    """Points that count toward store credit — capped at 150/month."""
    return min(raw_month_points(affiliate_id, month), config.MONTHLY_CREDIT_CAP_PTS)


def store_credit_dollars(affiliate_id, month=None) -> int:
    pts = credited_month_points(affiliate_id, month)
    return (pts // config.PTS_PER_DOLLAR_BLOCK) * 5


# ------------------------------------------------------------- FAQ log
def log_faq(question_text, asker_id, answered=False, answer_text=None):
    with _cursor() as c:
        c.execute(
            "INSERT INTO faq_log (question_text, asker_id, timestamp, answered, "
            "answer_text) VALUES (?,?,?,?,?)",
            (question_text, asker_id, dt.datetime.utcnow().isoformat(),
             1 if answered else 0, answer_text),
        )


def unanswered_faqs():
    with _cursor() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM faq_log WHERE answered=0 ORDER BY id DESC").fetchall()]


# --------------------------------------------------------------- kv store
def kv_get(key, default=None):
    with _cursor() as c:
        row = c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def kv_set(key, value):
    with _cursor() as c:
        c.execute("INSERT INTO kv (key, value) VALUES (?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))
