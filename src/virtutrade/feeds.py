"""Run one market feed in a background thread of the web process.

Hosts that allow a single always-on service (Render free, Codespaces) set
MARKET_FEED so prices keep moving without a second process. Run gunicorn with
one worker and no --preload: each worker would otherwise open its own feed,
and a thread started before the fork would not survive it.
"""

import asyncio
import logging
import sqlite3
import threading

LOGGER = logging.getLogger(__name__)
FEEDS = ('off', 'dnse', 'simulation')


def run_dnse(database):
    from virtutrade.database import init_database
    from virtutrade.dnse.snapshot import run_market_feed
    from virtutrade.dnse.worker import Settings

    init_database(database)
    asyncio.run(run_market_feed(Settings.from_environment(database), database))


def run_simulation(database, interval, stop):
    from virtutrade.simulation.market import run_simulator

    run_simulator(database, interval=interval, stop=stop)


def start_background_feed(app, *, stop=None):
    """Start the configured feed; return its thread, or None when MARKET_FEED is off."""
    kind = app.config.get('MARKET_FEED', 'off')
    if kind not in FEEDS:
        raise ValueError(f'MARKET_FEED must be one of: {", ".join(FEEDS)}')
    if kind == 'off':
        return None
    database = app.config['DATABASE']
    stop = stop or threading.Event()

    def run():
        from virtutrade.dnse.worker import FeedError

        try:
            if kind == 'dnse':
                run_dnse(database)
            else:
                run_simulation(database, app.config.get('SIMULATION_TICK_SECONDS', 20), stop)
        except FeedError as exc:
            # Locally authored text only; the web app keeps serving stored prices.
            LOGGER.error('Market feed stopped: %s', exc)
        except sqlite3.Error:
            LOGGER.exception('Market feed stopped: database unavailable or wrong mode.')

    thread = threading.Thread(target=run, name=f'{kind}-feed', daemon=True)
    thread.start()
    return thread
