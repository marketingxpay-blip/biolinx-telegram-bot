"""End-to-end logic tests — no live Telegram needed.

Run: python tests/test_logic.py   (exit 0 = all passed)
Covers: caption bank, game engine, DB limits/points/badges, FAQ grounding,
copy rendering. This is the "self-test every flow" step for everything that
doesn't require a live Telegram connection (those steps are in the README
smoke test, gated on Jakob's token + group).
"""
import asyncio
import os
import random
import sys
import tempfile

# Point the DB at a throwaway file BEFORE importing db.
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import config, db, game            # noqa: E402
from bot.captions import CAPTIONS           # noqa: E402
from bot import faq_ai                       # noqa: E402
from bot import copy as C                    # noqa: E402

PASSED = 0
FAILED = 0


def check(name, cond):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ok   {name}")
    else:
        FAILED += 1
        print(f"  FAIL {name}")


# ------------------------------------------------------------ caption bank
def test_caption_bank():
    print("caption bank")
    check("40 captions", len(CAPTIONS) == 40)
    check("all verdicts valid",
          all(v in ("PASS", "FLAG") for _, v, _ in CAPTIONS))
    check("every caption has a reason", all(r.strip() for _, _, r in CAPTIONS))
    check("no difficulty tags leaked into text",
          not any(t.startswith("[") for t, _, _ in CAPTIONS))
    passes = sum(1 for _, v, _ in CAPTIONS if v == "PASS")
    flags = sum(1 for _, v, _ in CAPTIONS if v == "FLAG")
    check("mix of pass and flag", passes == 18 and flags == 22)


# --------------------------------------------------------------- game engine
def test_game():
    print("game engine")
    rng = random.Random(42)
    rnd = game.new_round(rng)
    check("round has 10 questions", len(rnd.order) == 10)
    check("no duplicate captions in a round", len(set(rnd.order)) == 10)

    # Play a perfect round by always answering the correct verdict.
    streak_callouts = []
    for _ in range(10):
        _, verdict, _ = rnd.current_caption
        res = game.answer(rnd, verdict)
        if res["streak_callout"]:
            streak_callouts.append(res["streak_callout"])
    check("perfect round scores 10", rnd.score == 10)
    check("round finished", rnd.finished)
    check("streak callouts fired at 3/5/7",
          streak_callouts == ["3 in a row", "5 in a row", "7 in a row"])
    passed, badge = game.outcome(rnd)
    check("perfect -> passed + badge", passed and badge)

    # First-tap lock: answering again on a finished round raises.
    try:
        game.answer(rnd, "PASS")
        check("locked after finish", False)
    except ValueError:
        check("locked after finish", True)

    # A wrong answer breaks the streak.
    rng2 = random.Random(7)
    rnd2 = game.new_round(rng2)
    _, verdict, _ = rnd2.current_caption
    wrong = "FLAG" if verdict == "PASS" else "PASS"
    res = game.answer(rnd2, wrong)
    check("wrong answer not counted", res["score"] == 0 and res["streak"] == 0)

    # 6 correct then stop -> not a pass (needs 7).
    rng3 = random.Random(1)
    rnd3 = game.new_round(rng3)
    for i in range(10):
        _, verdict, _ = rnd3.current_caption
        game.answer(rnd3, verdict if i < 6 else
                    ("FLAG" if verdict == "PASS" else "PASS"))
    passed, badge = game.outcome(rnd3)
    check("6/10 is not a pass", rnd3.score == 6 and not passed and not badge)


# ------------------------------------------------------------------ database
def test_db():
    print("database")
    db.init_db()
    aff = "aff:test1"

    # Points: award poll once/day.
    check("poll awards once", db.award_poll(aff) is True)
    check("poll blocked 2nd time same day", db.award_poll(aff) is False)
    db.award_qotd(aff)
    db.award_reply(aff)               # +2
    db.award_reply(aff)               # +2
    # 1 (poll) + 1 (qotd) + 2 + 2 = 6
    check("raw points sum correct", db.raw_month_points(aff) == 6)

    # 150/month cap.
    aff2 = "aff:cap"
    for _ in range(200):
        db.award_reply(aff2)          # 200 * 2 = 400 raw
    check("raw uncapped", db.raw_month_points(aff2) == 400)
    check("credited capped at 150", db.credited_month_points(aff2) == 150)
    check("store credit reflects cap", db.store_credit_dollars(aff2) == 5 * (150 // 100))

    # Reaction award once per message.
    check("reaction awards once", db.award_reactions(9001, aff) is True)
    check("reaction blocked for same msg", db.award_reactions(9001, aff) is False)

    # Pass or Flag tries/day + entries cap + badge.
    aff3 = "aff:play"
    e1, b1 = db.record_session(aff3, 111, 8)    # 8/10 -> entry
    e2, b2 = db.record_session(aff3, 111, 7)    # 7/10 -> entry
    e3, b3 = db.record_session(aff3, 111, 10)   # 10/10 -> entry(capped?) + badge
    check("first pass earns entry", e1 == 1)
    check("badge on perfect", b3 == 1)
    check("3 tries used", db.tries_today(aff3) == 3)
    check("entries capped at 3/day", db.entries_today(aff3) <= 3)
    allowed, _ = db.can_play(aff3)
    check("blocked after 3 tries", allowed is False)
    check("badge counted", db.badge_count(aff3) == 1)


# --------------------------------------------------------------- FAQ grounding
def test_faq():
    print("FAQ grounding (keyword fallback, no API key)")
    # Ensure no API key so we test the grounded fallback path deterministically.
    config.ANTHROPIC_API_KEY = ""

    async def run():
        r1, ok1 = await faq_ai.answer_question("How do points work?")
        r2, ok2 = await faq_ai.answer_question("What's a Bio Badge?")
        r3, ok3 = await faq_ai.answer_question("When do I get paid?")
        r4, ok4 = await faq_ai.answer_question("Can you write my ad copy for me?")
        return (r1, ok1), (r2, ok2), (r3, ok3), (r4, ok4)

    (r1, ok1), (r2, ok2), (r3, ok3), (r4, ok4) = asyncio.run(run())
    check("points question answered", ok1 and "100 pts" in r1)
    check("badge question answered", ok2 and "10/10" in r2)
    check("all answers signed Lincoln", all("Lincoln" in r for r in (r1, r2, r3, r4)))
    check("pending payout -> fallback + logged",
          (not ok3) and C.FAQ_FALLBACK in r3)
    check("off-rulebook question -> fallback (never improvises)",
          (not ok4) and C.FAQ_FALLBACK in r4)


# ------------------------------------------------------------------- copy
def test_copy():
    print("copy rendering")
    check("home pin non-empty", "YOUR GUIDE TO THIS GROUP" in C.HOME_PIN)
    pf = C.pass_or_flag_pin("JULY")
    check("pass/flag month fills", "JULY REWARDS" in pf and "July's Bio Badge" in pf)
    g = C.games_pin(9, [{"name": "A", "tier": "Gold", "referral_count": 5}])
    check("games pin renders top3 + placeholders",
          "9 days left" in g and "1st: A (Gold) -- 5 referrals" in g and "2nd: --" in g)
    check("bio-lounge pin non-empty", "Bio-Lounge" in C.BIO_LOUNGE_PIN)
    check("got questions pin non-empty", "we gave you answers" in C.GOT_QUESTIONS_PIN)
    check("qotd bank has 12", len(C.QOTD_BANK) == 12)
    check("poll bank has 5", len(C.POLL_BANK) == 5)


def main():
    test_caption_bank()
    test_game()
    test_db()
    test_faq()
    test_copy()
    print(f"\n{PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
