"""The installed CLI must work outside the checkout without PYTHONPATH tricks."""

import os
import sqlite3
import subprocess
import sys
from contextlib import closing


def test_installed_module_seeds_from_another_directory(tmp_path):
    database = tmp_path / 'cli.db'
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    environment['DATABASE_PATH'] = str(database)
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, '-m', 'virtutrade', 'init-db'],
            cwd=tmp_path, env=environment, check=True, capture_output=True,
            text=True, timeout=20,
        )
        assert 'Database ready: 12 price_quote rows' in result.stdout
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute('SELECT COUNT(*) FROM instrument').fetchone()[0] == 12
        assert connection.execute('SELECT COUNT(*) FROM price_quote').fetchone()[0] == 12
