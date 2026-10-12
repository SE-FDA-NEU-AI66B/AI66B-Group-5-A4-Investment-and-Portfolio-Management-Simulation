"""Resolve local configuration independently of the shell's working directory."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# SETUP installs this checkout in editable mode; data and .env remain at its root.
ROOT = Path(__file__).resolve().parents[2]


def load_config():
    load_dotenv(ROOT / '.env')
    database = Path(os.environ.get('DATABASE_PATH', 'instance/virtutrade.db'))
    if not database.is_absolute():
        database = ROOT / database
    # Signs CSRF tokens. Production must set SECRET_KEY in .env; without one
    # each boot mints a fresh random secret (pending forms/sessions from a
    # previous boot stop validating, which is the safe default).
    secret = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    return {'DATABASE': str(database), 'SECRET_KEY': secret}
