"""Run with python -m virtutrade [run|init-db|init-demo|stream|public-feed|simulate] after installing."""

import argparse
import os

from virtutrade.app import create_app
from virtutrade.database import init_database


def main():
    parser = argparse.ArgumentParser(prog='python -m virtutrade',
                                     description='VirtuTrade M2 walking skeleton')
    parser.add_argument('command', nargs='?',
                        choices=['run', 'init-db', 'init-demo', 'stream', 'public-feed', 'simulate'],
                        default='run')
    args = parser.parse_args()
    application = create_app()
    if args.command == 'init-db':
        count = init_database(application.config['DATABASE'])
        print(f'Database ready: {count} price_quote rows (12 on a fresh database).')
    elif args.command == 'init-demo':
        from virtutrade.simulation.repository import init_demo
        if application.config.get('QUOTE_MODE') != 'simulation':
            parser.exit(1, 'Set QUOTE_MODE=simulation and a new DATABASE_PATH first.\n')
        try:
            init_demo(application.config['DATABASE'])
        except FileExistsError:
            parser.exit(1, 'Database already exists; use Generate demo quotes instead of resetting it.\n')
        print('Simulation database ready: 12 generated quotes; open Market and Register to start.')
    elif args.command == 'stream':
        import asyncio
        import logging
        import sqlite3

        from virtutrade.dnse.snapshot import run_market_feed
        from virtutrade.dnse.worker import FeedError, Settings
        logging.basicConfig(level=logging.INFO)
        try:
            # Idempotent: adds tables introduced since the database was created.
            init_database(application.config['DATABASE'])
            settings = Settings.from_environment(application.config['DATABASE'])
            asyncio.run(run_market_feed(settings, application.config['DATABASE']))
        except FeedError as exc:
            parser.exit(1, str(exc) + '\n')
        except sqlite3.Error:
            parser.exit(1, 'Database unavailable; check setup and init-db.\n')
        except KeyboardInterrupt:
            pass
    elif args.command == 'public-feed':
        import logging
        import sqlite3

        from virtutrade.dnse.public import run_public_feed
        logging.basicConfig(level=logging.INFO)
        try:
            init_database(application.config['DATABASE'])
            run_public_feed(application.config['DATABASE'])
        except sqlite3.Error:
            parser.exit(1, 'Database unavailable or a simulation database; use a DNSE database.\n')
        except KeyboardInterrupt:
            pass
    elif args.command == 'simulate':
        import logging
        import sqlite3

        from virtutrade.simulation.market import run_simulator
        logging.basicConfig(level=logging.INFO)
        if application.config.get('QUOTE_MODE') != 'simulation':
            parser.exit(1, 'Set QUOTE_MODE=simulation and run init-demo first.\n')
        try:
            init_database(application.config['DATABASE'])
            run_simulator(application.config['DATABASE'],
                          interval=application.config['SIMULATION_TICK_SECONDS'])
        except sqlite3.Error:
            parser.exit(1, 'The simulator needs a simulation database; run init-demo first.\n')
        except KeyboardInterrupt:
            pass
    else:
        from virtutrade.feeds import start_background_feed
        if application.config.get('MARKET_FEED', 'off') != 'off':
            import logging
            logging.basicConfig(level=logging.INFO)
        start_background_feed(application)
        application.run(host=os.environ.get('HOST', '127.0.0.1'),
                        port=int(os.environ.get('PORT', '5000')), debug=False)


if __name__ == '__main__':
    main()
