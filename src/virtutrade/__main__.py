"""Run with python -m virtutrade [run|init-db] after installing the checkout."""

import argparse
import os

from virtutrade.app import create_app
from virtutrade.database import init_database


def main():
    parser = argparse.ArgumentParser(prog='python -m virtutrade',
                                     description='VirtuTrade M2 walking skeleton')
    parser.add_argument('command', nargs='?', choices=['run', 'init-db', 'init-demo'], default='run')
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
    else:
        application.run(host=os.environ.get('HOST', '127.0.0.1'),
                        port=int(os.environ.get('PORT', '5000')), debug=False)


if __name__ == '__main__':
    main()
