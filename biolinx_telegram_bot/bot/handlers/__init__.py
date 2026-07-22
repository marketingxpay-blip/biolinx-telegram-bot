"""Handler registration. Each module exposes register(dp)."""
from . import pass_or_flag, bio_lounge, games, got_questions, util


def register_all(dp):
    # Order matters: specific command/callback handlers first, broad
    # topic-scoped text handlers last.
    util.register(dp)          # /id + forward-to-id (setup helpers)
    pass_or_flag.register(dp)
    got_questions.register(dp)
    bio_lounge.register(dp)
    # games has no message handlers (schedule-driven); nothing to register.
