"""Got Questions AI — Claude, grounded STRICTLY to the approved rulebook.

The model may answer only from the approved Q&A set (copy.FAQ_ANSWERS, the
only items with a non-null answer). Anything not covered returns the exact
fallback line so the bot never improvises on compliance. Every reply is
signed "— Lincoln".

If ANTHROPIC_API_KEY is unset, this degrades to a pure keyword match against
the approved set (still safe, just no fuzzy matching).
"""
import logging

from . import config
from .copy import FAQ_ANSWERS, FAQ_SIGNATURE, FAQ_FALLBACK

log = logging.getLogger("faq_ai")


def _approved_block() -> str:
    lines = []
    for q, a in FAQ_ANSWERS.items():
        if a:
            lines.append(f"Q: {q}\nA: {a}")
    return "\n\n".join(lines)


SYSTEM_PROMPT = (
    "You are Lincoln, the Biolinx affiliate support assistant. You answer ONLY "
    "from the approved rulebook below. If the member's question is not clearly "
    "covered by it, respond with EXACTLY this text and nothing else: "
    f'"{FAQ_FALLBACK}". Never guess, never improvise, never use outside '
    "knowledge — especially on compliance, payouts, or anything not in the "
    "rulebook. Keep answers to the approved wording. Do not add a signature; "
    "it is appended for you.\n\n"
    "APPROVED RULEBOOK:\n{rulebook}"
)


def _sign(text: str) -> str:
    text = text.strip()
    if not text:
        return f"{FAQ_FALLBACK}\n\n{FAQ_SIGNATURE}"
    return f"{text}\n\n{FAQ_SIGNATURE}"


def _keyword_fallback(question: str):
    """Exact/substring match against approved answers (no API needed)."""
    q = question.lower().strip().rstrip("?")
    for key, ans in FAQ_ANSWERS.items():
        if ans and (key.lower().rstrip("?") in q or q in key.lower()):
            return ans
    return None


async def answer_question(question: str):
    """Return (reply_text, answered_bool). answered_bool=False => log it."""
    approved = _approved_block()

    if not config.ANTHROPIC_API_KEY:
        hit = _keyword_fallback(question)
        if hit:
            return _sign(hit), True
        return _sign(FAQ_FALLBACK), False

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = await client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT.format(rulebook=approved),
            messages=[{"role": "user", "content": question}],
        )
        text = "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        ).strip()
    except Exception as e:
        log.warning("Claude call failed, using keyword fallback: %s", e)
        hit = _keyword_fallback(question)
        if hit:
            return _sign(hit), True
        return _sign(FAQ_FALLBACK), False

    answered = FAQ_FALLBACK.lower() not in text.lower()
    return _sign(text), answered
