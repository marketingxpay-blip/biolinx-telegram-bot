"""Pass or Flag round engine — pure logic, no Telegram dependency.

Kept framework-free so the whole game is unit-testable without a live bot.
The handler (handlers/pass_or_flag.py) owns Telegram I/O and calls into this.
"""
import random
from dataclasses import dataclass, field
from typing import List

from . import config
from .captions import CAPTIONS


@dataclass
class Round:
    order: List[int]            # 10 caption-bank indices, randomized per player
    pos: int = 0                # index into `order` of the current question
    score: int = 0             # correct answers so far
    answered: int = 0          # questions answered so far
    streak: int = 0            # current consecutive-correct streak
    locked: set = field(default_factory=set)  # positions already answered

    @property
    def finished(self) -> bool:
        return self.answered >= config.ROUND_SIZE

    @property
    def current_index(self) -> int:
        return self.order[self.pos]

    @property
    def current_caption(self):
        return CAPTIONS[self.current_index]


def new_round(rng: random.Random = None) -> Round:
    """Pick ROUND_SIZE captions at random, order randomized per player.

    Per-member randomization is the anti answer-sharing lock: two players
    never see the same sequence.
    """
    rng = rng or random.Random()
    order = rng.sample(range(len(CAPTIONS)), config.ROUND_SIZE)
    return Round(order=order)


def answer(rnd: Round, choice: str):
    """Apply an answer to the current question. choice in {'PASS','FLAG'}.

    First tap locks the question (anti-retry). Returns a dict:
      {correct, reason, verdict, score, answered, streak, streak_callout, finished}
    Raises ValueError if the round is already finished or the position is
    somehow re-answered (defensive; the handler also disables buttons).
    """
    if rnd.finished:
        raise ValueError("round already finished")
    if rnd.pos in rnd.locked:
        raise ValueError("question already answered")

    text, verdict, reason = rnd.current_caption
    correct = (choice == verdict)

    rnd.locked.add(rnd.pos)
    rnd.answered += 1
    if correct:
        rnd.score += 1
        rnd.streak += 1
    else:
        rnd.streak = 0

    callout = None
    if correct and rnd.streak in (3, 5, 7):
        callout = {3: "3 in a row", 5: "5 in a row", 7: "7 in a row"}[rnd.streak]

    # advance
    if not rnd.finished:
        rnd.pos += 1

    return {
        "correct": correct,
        "reason": reason,
        "verdict": verdict,
        "caption": text,
        "score": rnd.score,
        "answered": rnd.answered,
        "streak": rnd.streak,
        "streak_callout": callout,
        "finished": rnd.finished,
    }


def outcome(rnd: Round):
    """Post-round summary: (passed, earned_badge)."""
    return (rnd.score >= config.PASS_THRESHOLD,
            rnd.score >= config.PERFECT_SCORE)
