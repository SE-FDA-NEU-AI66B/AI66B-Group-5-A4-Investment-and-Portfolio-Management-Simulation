"""Run with python -m virtutrade [run|init-db] after installing the checkout."""

import argparse
import os

from virtutrade.app import create_app
from virtutrade.database import init_database


def main():
    parser = argparse.ArgumentParser(prog='python -m virtutrade',
                                     description='VirtuTrade M2 walking skeleton')
    parser.add_argument('command', nargs='?', choices=['run', 'init-db', 'stream'], default='run')
    args = parser.parse_args()
    application = create_app()
    if args.command == 'init-db':
        count = init_database(application.config['DATABASE'])
        print(f'Database ready: {count} price_quote rows (12 on a fresh database).')
    elif args.command == 'stream':
        import asyncio
        import logging
        import sqlite3

        from virtutrade.dnse.worker import FeedError, Settings, run_feed
        logging.basicConfig(level=logging.INFO)
        try:
            settings = Settings.from_environment(application.config['DATABASE'])
            asyncio.run(run_feed(settings, application.config['DATABASE']))
        except FeedError as exc:
            parser.exit(1, str(exc) + '\n')
        except sqlite3.Error:
            parser.exit(1, 'Database unavailable; check setup and init-db.\n')
        except KeyboardInterrupt:
            pass
    else:
        application.run(host=os.environ.get('HOST', '127.0.0.1'),
                        port=int(os.environ.get('PORT', '5000')), debug=False)


if __name__ == '__main__':
    main()
