"""Resolve local configuration independently of the shell's working directory."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def load_config():
    load_dotenv(ROOT / '.env')
    database = Path(os.environ.get('DATABASE_PATH', 'instance/virtutrade.db'))
    if not database.is_absolute():
        database = ROOT / database
    return {'DATABASE': str(database)}
