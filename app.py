"""Command-line entry point; feature implementation lives in virtutrade/."""

import argparse
import os

from virtutrade import create_app
from virtutrade.database import init_database

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='VirtuTrade M2 walking skeleton')
    parser.add_argument('command', nargs='?', choices=['run', 'init-db'], default='run')
    args = parser.parse_args()
    application = create_app()
    if args.command == 'init-db':
        count = init_database(application.config['DATABASE'])
        print(f'Database ready: {count} price_quote rows (12 on a fresh database).')
    else:
        application.run(host=os.environ.get('HOST', '127.0.0.1'),
                        port=int(os.environ.get('PORT', '5000')), debug=False)
