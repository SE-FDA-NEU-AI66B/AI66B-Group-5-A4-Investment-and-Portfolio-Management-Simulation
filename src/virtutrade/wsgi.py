"""Production entry point: gunicorn --workers 1 --threads 8 virtutrade.wsgi:app

MARKET_FEED (off, dnse or simulation) optionally runs the market feed in this
process; see virtutrade.feeds for why the worker count must stay at one.
"""

import logging

from virtutrade.app import create_app
from virtutrade.feeds import start_background_feed

logging.basicConfig(level=logging.INFO)
app = create_app()
start_background_feed(app)
