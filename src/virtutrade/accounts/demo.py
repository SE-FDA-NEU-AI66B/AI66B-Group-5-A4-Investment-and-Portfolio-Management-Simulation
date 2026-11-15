"""Shared investor test accounts for the hosted app, listed in the README.

The password is a published test value, never a real one: anyone may sign in
with it, so these accounts hold only virtual money. There are three so that
one locked account (five wrong passwords lock it for 15 minutes) does not
block a demonstration. `.test` is a reserved domain, so no mail can reach it.
"""

from virtutrade.accounts import errors, service

TEST_ACCOUNTS = (
    "investor1@virtutrade.test",
    "investor2@virtutrade.test",
    "investor3@virtutrade.test",
)
TEST_PASSWORD = "PaperTrade-2026"


def seed_test_accounts(db_path, *, now=None):
    """Create missing test accounts with the normal one-time grant; return the new ones."""
    created = []
    for email in TEST_ACCOUNTS:
        try:
            service.register(db_path, email=email, password=TEST_PASSWORD, now=now)
        except errors.EmailInUse:
            continue
        created.append(email)
    return created
