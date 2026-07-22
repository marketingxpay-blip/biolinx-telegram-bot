# Biolinx Affiliate Telegram Bot

aiogram 3.x · SQLite · long-polling · Railway-ready. Built to the
`BIOLINX_AFFILIATE_TELEGRAM_BUILD_DOC` and `TELEGRAM_API_CLAUDE_CODE_DEV_REFERENCE`.

All five tabs are built and logic-tested. What's left is three things only a
human with the credentials can do: paste the bot token, create the Telegram
group + channel, and click deploy on Railway. Runbook below — about 15 minutes.

---

## What's in here

```
main.py                 entry point (long-polling)
bot/config.py           env + locked constants (points, rules)
bot/db.py               SQLite: points, streaks, badges, entries, FAQ log
bot/game.py             Pass or Flag round engine (pure logic)
bot/captions.py         the 40-caption bank (verbatim)
bot/copy.py             every pinned message, verbatim from the build doc
bot/ephemeral.py        raw HTTP for the Bot API 10.2 ephemeral methods
bot/faq_ai.py           Got Questions AI, grounded to the approved rulebook
bot/raza_feed.py        leaderboard feed adapter (dummy data until Raza's)
bot/scheduler.py        daily poll, QotD, leaderboard refresh (UTC)
bot/setup_group.py      one-time: create topics, post + pin all copy
bot/handlers/           pass_or_flag, bio_lounge, games, got_questions
tests/test_logic.py     40 checks, all green (run: python tests/test_logic.py)
railway.toml Procfile requirements.txt runtime.txt .env.example
```

---

## 1. Local run (to test before deploying)

```
pip install -r requirements.txt
cp .env.example .env      # then fill in TELEGRAM_BOT_TOKEN at minimum
python tests/test_logic.py   # should print "40 passed, 0 failed"
python main.py               # connects and long-polls
```

## 2. The bot token

The token was created in @BotFather but is **not** in this repo (correct — it
never should be). Get it from @BotFather (`/mybots` -> your bot -> API Token)
and put it in `.env` as `TELEGRAM_BOT_TOKEN=...`, or add it as a Railway
Variable. In BotFather also:

- `/setprivacy` -> **Disable** (required so the bot can read Bio-Lounge messages
  for point tracking and read questions in Got Questions).
- Set the @username (must end in `bot`) if not already done.

## 3. Create the Telegram group + channel (one time, in the app)

The bot can create the *topics* itself, but a human has to create the container
group and channel and make the bot an admin:

1. Create a **supergroup**, open its settings, and turn **Topics ON**.
2. Add the bot as an **admin** with *Manage Topics* and *Pin Messages* rights.
3. Create a **broadcast Channel** for Home. Add the bot as admin there too.
4. Find the IDs: run `python -m bot.setup_group --show-chat-id`, then post a
   message in the group and in the channel — their IDs print to the console.
   (Group/channel IDs start with `-100`.)
5. Put them in `.env` / Railway Variables:
   `BIOLINX_GROUP_ID`, `BIOLINX_HOME_CHANNEL_ID`, `BIOLINX_ADMIN_IDS`.

Then run the one-time setup, which creates the 4 topics and posts + pins all
copy (Home, Pass or Flag, Bio-Lounge, Got Questions, and the Games leaderboard):

```
python -m bot.setup_group
```

## 4. Deploy to Railway

1. Push this folder to a GitHub repo (private).
2. On railway.app: **New Project -> Deploy from GitHub repo** -> pick the repo.
3. Railway reads `railway.toml` and runs `python main.py` as a worker.
   No public URL / domain is needed — this bot uses long-polling.
4. In the service **Variables** tab, add every key from `.env.example` that has
   a value (at minimum `TELEGRAM_BOT_TOKEN`; add `ANTHROPIC_API_KEY` for live
   Got Questions AI, and the group/channel IDs).
5. **Persistent storage:** add a Railway **Volume** mounted at `/data` and set
   `DB_PATH=/data/biolinx.db` so points/streaks survive redeploys. (Without a
   volume the SQLite file resets on each deploy.)
6. Deploy. Watch the logs for `Starting @<bot> ... Long-polling.`

## 5. Anthropic API key (Got Questions AI)

Add `ANTHROPIC_API_KEY` to enable live grounded answers. Without it the tab
still works via exact keyword matching against the approved rulebook — it just
won't fuzzy-match phrasings. The AI is grounded: it answers **only** from the
approved Q&A set and returns "Good question, we'll get back to you." for
anything else, then logs it and pings admins.

---

## Still pending (by design — from the build doc)

These do not block launch; the bot handles each gracefully:

- **Raza's leaderboard feed** — set `RAZA_FEED_URL` (+ `RAZA_FEED_KEY`) when
  ready. Until then the Games tab shows clearly-labelled sample standings.
  Confirm the JSON shape matches `raza_feed.py` (a list of
  `{name, tier, referral_count}`) or adjust the adapter there.
- **Final prize / payout copy** — three Got Questions answers are still marked
  PENDING (`When do I get paid?`, `How do I get my link?`, `How do I redeem
  points?`). They correctly fall through to the "we'll get back to you" +
  admin-log path until filled in `bot/copy.py` (`FAQ_ANSWERS`).
- **Community goal number + reward**, **Bio Badge redemption value** — plug into
  `copy.monthly_winner(...)` when locked.
- **Hub / deep-link URLs** — pins show `[HUB_URL]` tokens on purpose so no one
  ships a guessed link. Set them in `bot/copy.py` (`HUB_URL`).
