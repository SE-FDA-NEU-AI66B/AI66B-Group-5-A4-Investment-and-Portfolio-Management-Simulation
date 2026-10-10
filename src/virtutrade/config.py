"""Resolve local configuration independently of the shell's working directory."""

import os
from pathlib import Path

from dotenv import load_dotenv

# SETUP installs this checkout in editable mode; data and .env remain at its root.
ROOT = Path(__file__).resolve().parents[2]


def load_config():
    load_dotenv(ROOT / '.env')
    database = Path(os.environ.get('DATABASE_PATH', 'instance/virtutrade.db'))
    if not database.is_absolute():
        database = ROOT / database
    return {'DATABASE': str(database), 'QUOTE_MODE': os.environ.get('QUOTE_MODE', 'seed')}
