"""VirtuTrade M2: one public, read-only market route backed by SQLite."""
import argparse
import os
import sqlite3
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, url_for

from database import init_database, read_market

ROOT = Path(__file__).resolve().parent


def create_app(config=None):
    load_dotenv(ROOT / '.env')
    app = Flask(__name__)
    database_path = Path(os.environ.get('DATABASE_PATH', 'instance/virtutrade.db'))
    if not database_path.is_absolute():
        database_path = ROOT / database_path
    app.config.update(DATABASE=str(database_path))
    if config:
        app.config.update(config)

    @app.template_filter('vnd')
    def vnd(value):
        return f'{value:,}'

    @app.get('/')
    def home():
        return redirect(url_for('market'))

    @app.get('/market')
    def market():
        try:
            quotes = read_market(app.config['DATABASE'])
        except sqlite3.Error:
            app.logger.exception('Could not read market database')
            return render_template('market.html', quotes=[], error=True), 503
        now = datetime.now(timezone.utc)
        for quote in quotes:
            # Monetary inputs stay integers; percentage formatting uses Decimal.
            change = (Decimal(quote['price_vnd'] - quote['previous_close_vnd'])
                      / Decimal(quote['previous_close_vnd']) * 100)
            quote['change'] = change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            try:
                timestamp = datetime.fromisoformat(quote['quoted_at'].replace('Z', '+00:00'))
                quote['stale'] = timestamp.tzinfo is None or (now - timestamp).total_seconds() > 900
            except (ValueError, TypeError):
                quote['stale'] = True
        return render_template('market.html', quotes=quotes, error=False)

    return app


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
