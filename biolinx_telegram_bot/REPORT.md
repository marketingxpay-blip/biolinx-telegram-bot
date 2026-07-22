# REPORT — Biolinx Affiliate Telegram Bot build

STATUS: Code 100% built and logic-tested (40/40 checks green). NOT live yet — blocked on 3 human/credential steps only Jakob can do. ~15 min to go live.

---

## What I did

Built the entire bot from scratch to the two build docs. Prior runs (1–6) only
produced comparison charts and mockups — there was zero bot code before tonight.
This is a complete aiogram 3.x application: all 5 tabs, all game and points
logic, SQLite persistence, the scheduler, the grounded FAQ AI, and the Railway
deploy config. 26 files, ~2,000 lines. Verified the load-bearing spec first:
the ephemeral-message API the whole /play flow depends on is real (Telegram Bot
API 10.2, shipped July 14 2026).

## What's done and tested

- Home channel guide — verbatim copy, posts + pins via setup.
- Pass or Flag — /play, ephemeral per-player rounds, 40-caption bank, ✅/🚩
  buttons, first-tap lock, per-member randomized order, 7/10 = entry,
  10/10 = Bio Badge, 3 tries/day, 3 entries/day cap, UTC reset.
- The Biolinx Games — pinned leaderboard, hourly in-place refresh, dummy data
  now, Raza adapter with fallback-to-last-good wired.
- Bio-Lounge — daily poll + Question of the Day on a UTC scheduler; points for
  poll (1), QotD (1), reply (2), reactions (3); 150 pts/mo credit cap + separate
  uncapped badge bucket.
- Got Questions — tappable FAQ buttons + free-text AI answers grounded STRICTLY
  to the approved rulebook, "we'll get back to you" fallback, question logging,
  admin ping, signed Lincoln.
- Self-test suite: 40 checks across captions, game engine, DB limits/points/
  badges, FAQ grounding, copy rendering — all green. Boot smoke test passes
  (handlers register, scheduler builds, token guard fires).

## What's open (blockers — need Jakob)

1. BOT TOKEN — not in .env, not in Drive. Bot can't connect without it. Paste
   into Railway Variables (or .env). This is the #1 blocker.
2. TELEGRAM GROUP + CHANNEL — must be created in the app: a supergroup with
   Topics ON, a broadcast channel for Home, bot added as admin on both. The bot
   auto-creates the 4 topics + posts all pins after that (one command). I can't
   do this step — it needs the app + the token.
3. RAILWAY DEPLOY — no Railway account/credential exists in this session. I
   cannot create an account or deploy unattended. Full runbook is in the README.

Also optional/pending by design (do NOT block launch):
- Anthropic API key for live Got Questions AI (degrades to keyword matching).
- Raza's feed URL/format (dummy standings until then).
- Final prize/payout copy: 3 FAQ answers + community goal + badge redemption
  value (they fall through to the safe fallback until filled).

## Where to check

In the biolinx-cowork Drive folder:
- `biolinx_telegram_bot.zip` — the full repo, ready to push to GitHub + deploy.
- `REPORT.md` (this file).
- `WORKLOG_run7_2026-07-21_SESSION044.md` — run log.

Inside the zip: `README.md` has the exact 5-step deploy runbook; run
`python tests/test_logic.py` to reproduce the 40/40 green.

## What needs a decision

- Paste the bot token + create the group/channel, then run `python -m
  bot.setup_group` — that's the whole go-live path once deployed.
- Confirm whether to deploy on Railway (README assumes it) or another host —
  the code runs on any always-on Python host unchanged.
