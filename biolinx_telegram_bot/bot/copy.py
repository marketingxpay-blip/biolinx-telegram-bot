"""All pinned-message copy, verbatim from build doc section 4.

Deep links / hub links are PENDING (build doc section 8). They are kept as
named placeholders so setup won't invent URLs; fill them in bot/links.py
when the real URLs exist. Copy wording itself is final and unchanged.
"""
import datetime as _dt

# ------------------------------------------------------------------ links
# PENDING per build doc section 8. Setup posts the copy with these tokens
# left visible so nobody mistakes a guessed URL for an approved one.
HUB_URL = "[HUB_URL]"

# --------------------------------------------------------------- 4.1 HOME
HOME_PIN = """\
YOUR GUIDE TO THIS GROUP

--- TABS ---

Home (you're here) -> your guide to this group
Pass or Flag -> play to win a free giveaway entry (monthly)
The Biolinx Games -> the top 3 affiliates win $50+ in Biolinx Bonuses
Bio-Lounge -> come be a person for a second
Got Questions? -> we got answers (and we reply fast)

--- COMMANDS ---

Each command only works in its own chat.

Pass or Flag
- /play -> start a new round

--- REWARDS ---

Earn points, redeem for store credit.

Daily poll -> 1 pt (Bio-Lounge)
Question of the Day -> 1 pt (Bio-Lounge)
Reply to an affiliate -> 2 pts (Bio-Lounge)
Get reactions -> 3 pts (Bio-Lounge)
Bio Badge -> 200 pts (Pass or Flag)

100 pts = $5 store credit (max 150/month)

--- BONUSES ---

Monthly Giveaway -> $25 store credit (Pass or Flag)
The Top 3 -> up to $150 store credit (The Biolinx Games)

--- AFFILIATE TOOLKIT ---

Start here
- Compliance Hub -> your full compliance playbook
- Rulebook -> every rule, one download

Make content
- The Checker -> know it's safe before you post
- Prompts -> ready prompts per platform
- 50 Content Ideas -> 50 compliant ideas so you can start today
- Asset Kit -> 20+ free Biolinx marketing assets

Reply to people
- Reply Scripts -> 30+ safe reply templates

Don't like reading compliance rules?
Click here to get compliant copy in 60 seconds"""

# -------------------------------------------------------- 4.2 PASS OR FLAG
def pass_or_flag_pin(month_name: str = None) -> str:
    month_name = month_name or _dt.datetime.utcnow().strftime("%B").upper()
    return f"""\
Is it compliant? Tap and find out.

New to compliance?
Use this to learn the rules -- What You Can and Can't Say {HUB_URL}#say

--- HOW TO PLAY ---

1. Type /play
2. Read the caption
3. Tap your answer:
   - compliant (checkmark)
   - not compliant (flag)

Quick example
CAPTION: "99% purity guaranteed"
ANSWER: not compliant (never post a number)

--- THE RULES ---

Score 7 of 10 to earn a free entry.
- 3 tries daily
- Earn up to 3 entries a day (max)
- Answers are final

Warning: Leaving mid-round ends your turn.

{month_name} REWARDS
Score 7+ -> free entry to win $25 store credit
Score 10 -> earn {month_name.title()}'s Bio Badge (worth collecting)

Type /play to start"""


# 4.3 Pass or Flag — ephemeral bot replies
def round_caption_prompt(caption_text: str) -> str:
    return f'Round\'s up\n\n"{caption_text}"\n\ncompliant or not compliant?'


def reply_correct(reason: str, score: int, answered: int) -> str:
    return f"Correct\n{reason}\n\nScore: {score}/{answered}"


def reply_wrong(reason: str, score: int, answered: int) -> str:
    return f"Wrong\n{reason}\n\nScore: {score}/{answered}"


STREAK_CALLOUTS = {3: "3 in a row", 5: "5 in a row", 7: "7 in a row"}

# --------------------------------------------------- 4.5 THE BIOLINX GAMES
def games_pin(days_left: int, top3: list) -> str:
    """top3: list of dicts {name, tier, referral_count} (already sorted)."""
    lines = []
    labels = ["1st", "2nd", "3rd"]
    for i in range(3):
        if i < len(top3):
            r = top3[i]
            lines.append(f"{labels[i]}: {r['name']} ({r['tier']}) -- "
                         f"{r['referral_count']} referrals")
        else:
            lines.append(f"{labels[i]}: --")
    top_block = "\n".join(lines)
    return f"""\
{days_left} days left this month

--- TOP 3 RIGHT NOW ---

{top_block}

--- BONUSES ---

$150 / $75 / $50
*store credit

--- 3 WAYS TO RAISE YOUR RANK ---

1. Set a weekly referral goal
2. Post about Biolinx every week
3. Reach out to new people daily

Get started in 60 seconds"""


# 4.6 Monthly winner announcement
def monthly_winner(month, winners, all_time_payout, next_month,
                   month_to_date, goal, reward) -> str:
    labels = ["1st", "2nd", "3rd"]
    wl = "\n".join(
        f"{labels[i]}: {winners[i] if i < len(winners) else '--'}"
        for i in range(3)
    )
    return f"""\
{month} WINNERS

{wl}

${all_time_payout} paid to affiliates all-time

--- {next_month} CHALLENGE ---

${month_to_date} / ${goal}
If we hit ${goal}, EVERYONE gets {reward}

Let's bring it home."""


# ---------------------------------------------------------- 4.7 BIO-LOUNGE
BIO_LOUNGE_PIN = """\
Welcome to the Bio-Lounge.

Kick back and hang out. No pitches, just affiliates talking.

--- HOUSE RULES ---

- Be cool to each other
- No selling, no self-promo
- Compliant talk only (mostly joking)

--- HOW 2 EARN ---

Answer the daily poll (1 point)
Answer the Question of the Day (1 point)
Reply to another affiliate (2 points)
Get reactions on your post (3 points)

Or just start a conversation.

100 pts = $5 store credit (max 150/month)"""

# 4.8 Question of the Day bank (rotates daily)
QOTD_BANK = [
    "How long have you been an affiliate?",
    "What platform do you post on most?",
    "What got you into affiliate marketing?",
    "Best advice another affiliate gave you?",
    "One post you're actually proud of?",
    "Morning poster or night poster?",
    "Coffee or energy drink on a content day?",
    "What's the hardest part of posting for you?",
    "What's a win you had this week, big or small?",
    "If you could fix one thing about affiliate life, what?",
    "What are you working on right now?",
    "Drop a gif that sums up your week.",
]

# 4.9 Daily poll bank (tap-to-react)
POLL_BANK = [
    ("Coffee or energy drink?", ["Coffee", "Energy drink"]),
    ("Instagram or TikTok?", ["Instagram", "TikTok"]),
    ("Morning or night poster?", ["Morning", "Night"]),
    ("Reels or carousels?", ["Reels", "Carousels"]),
    ("Plan ahead or post on the fly?", ["Plan ahead", "On the fly"]),
]

# -------------------------------------------------------- 4.10 GOT QUESTIONS
GOT_QUESTIONS_PIN = f"""\
You had questions, so we gave you answers

--- POSTING ---

Is my post safe? -> The Checker
What can I say? -> What You Can and Can't Say
What can I show? -> What You Can Show
Where does #ad go? -> Where to Put #ad

--- MAKING CONTENT ---

What are the rules? -> The Rulebook
What do I post? -> 50 Content Ideas
What do I reply? -> Reply Scripts
Where are the graphics? -> Promo Asset Kit

Open the Compliance Hub -- {HUB_URL}"""

# 4.11 Got Questions — tappable FAQ buttons + approved answers
# This dict is the AI's ONLY source for compliance answers. Signed Lincoln.
FAQ_BUTTONS = [
    "When do I get paid?",
    "How do I get my link?",
    "How do points work?",
    "What's a Bio Badge?",
    "How do I redeem points?",
]

FAQ_ANSWERS = {
    "How do points work?":
        "100 pts = $5 store credit. Earn up to 150 pts a month.",
    "What's a Bio Badge?":
        "Win one by scoring 10/10 in Pass or Flag. Worth 200 pts. Collect them.",
    # PENDING answers — build doc 4.11. Left as None so the fallback fires
    # instead of a guessed answer.
    "When do I get paid?": None,
    "How do I get my link?": None,
    "How do I redeem points?": None,
}

FAQ_SIGNATURE = "— Lincoln"
FAQ_FALLBACK = "Good question, we'll get back to you."
