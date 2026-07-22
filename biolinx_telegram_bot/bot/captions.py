"""Pass or Flag caption bank — 40 captions, verbatim from build doc 4.4.

Each entry: (text, verdict, reason).
  verdict: "PASS" (compliant) or "FLAG" (not compliant).
  reason : shown to the player after they answer.

Difficulty tags [E]/[M]/[H] in the doc are BUILD-ONLY and intentionally
NOT stored here — they are never shown to players.
"""

CAPTIONS = [
    ("Cures joint pain", "FLAG", "health claim"),
    ("Ships with a COA", "PASS", "proof"),
    ("99% purity guaranteed", "FLAG", "never post a number"),
    ("For research use only", "PASS", "correct framing"),
    ("My clients love their results", "FLAG", "implies human use"),
    ("Third-party lab tested", "PASS", "verifiable, no claim"),
    ("Melts fat fast", "FLAG", "health claim"),
    ("See the COA on every batch", "PASS", "points to proof"),
    ("Not medical advice, but it changed my life", "FLAG",
     "disclaimer doesn't save a claim"),
    ("Sourced from a US lab", "PASS", "fact, no claim"),
    ("I take it every morning", "FLAG", "never say a person uses it"),
    ("Lab results are public", "PASS", "proof"),
    ("Clinically proven to work", "FLAG", "cites results"),
    ("G2-T available now", "PASS", "coded name, no claim"),
    ("DM me for dosing help", "FLAG", "dosing talk"),
    ("Reconstitution guide on the site", "PASS", "info, no claim"),
    ("Down 15lbs, ask me how", "FLAG", "personal use + result"),
    ("COA on every product page", "PASS", "points to proof"),
    ("IYKYK, down 20", "FLAG", "coded result still a result"),
    ("Supports research applications", "PASS", "research framing"),
    ("It cured my inflammation", "FLAG", "health claim + personal use"),
    ("Compare the lab data yourself", "PASS", "proof, no claim"),
    ("95% of users saw results", "FLAG", "cites results + human use"),
    ("#ad on a promo post", "PASS", "correct disclosure"),
    ("#wellness #glp1 #results", "FLAG", "banned hashtag hidden in tags"),
    ("Restores youthful energy", "FLAG", "health claim"),
    ("Read the third-party COA here", "PASS", "proof only"),
    ("Great for recovery after training", "FLAG", "implies use + benefit"),
    ("US-based, research-use only", "PASS", "correct framing"),
    ("Basically Ozempic but cheaper", "FLAG", "drug name + comparison"),
    ("Studies show it boosts energy", "FLAG", "cites studies + benefit"),
    ("Verified lab report on file", "PASS", "proof"),
    ("Everyone's getting amazing results", "FLAG", "cites results"),
    ("Boosts metabolism", "FLAG", "health claim"),
    ("Batch-tested for quality", "PASS", "no number, no claim"),
    ("Ask me what I stack it with", "FLAG", "implies personal use"),
    ("G1-S back in stock", "PASS", "coded name"),
    ("Lose weight in 2 weeks", "FLAG", "health claim + result"),
    ("Not for human use (winking)", "FLAG", "wink undoes the disclaimer"),
    ("Full COA linked in bio", "PASS", "points to proof"),
]


def caption(index: int):
    """Return (text, verdict, reason) for a bank index."""
    return CAPTIONS[index]
