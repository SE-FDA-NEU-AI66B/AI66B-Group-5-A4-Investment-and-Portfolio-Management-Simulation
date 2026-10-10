"""Application factory: configure Flask and register each feature module."""

from flask import Flask, redirect, url_for

from virtutrade.config import load_config
from virtutrade.market import blueprint as market_blueprint
from virtutrade.market.repository import SQLiteQuoteRepository
from virtutrade.market.routes import api_blueprint


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(load_config())
    if config:
        app.config.update(config)
    # Compose infrastructure here; controllers/services do not select a database.
    app.extensions['market_reader_factory'] = lambda: SQLiteQuoteRepository(app.config['DATABASE'])
    app.register_blueprint(market_blueprint, url_prefix='/market')
    app.register_blueprint(api_blueprint, url_prefix='/api/market')

    @app.get('/')
    def home():
        return redirect(url_for('market.index'))

    return app
