"""Application factory: configure Flask and register each feature module."""

from flask import Flask, redirect, url_for

from virtutrade.accounts import blueprint as accounts_blueprint
from virtutrade.accounts.routes import init_auth
from virtutrade.config import load_config
from virtutrade.market import blueprint as market_blueprint
from virtutrade.market.repository import SQLiteQuoteRepository
from virtutrade.market.routes import api_blueprint
from virtutrade.orders.routes import blueprint as orders_blueprint


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(load_config())
    if config:
        app.config.update(config)
    # Compose infrastructure here; controllers/services do not select a database.
    app.extensions['market_reader_factory'] = lambda: SQLiteQuoteRepository(
        app.config['DATABASE'], provider_only=app.config.get('QUOTE_MODE') == 'dnse')
    app.register_blueprint(accounts_blueprint)
    app.register_blueprint(market_blueprint, url_prefix='/market')
    app.register_blueprint(api_blueprint, url_prefix='/api/market')
    app.register_blueprint(orders_blueprint)
    init_auth(app)

    @app.context_processor
    def feature_navigation():
        # Long owns /portfolio. Expose a link only when the real GET route lands.
        return {'portfolio_url': next((rule.rule for rule in app.url_map.iter_rules()
                                       if rule.rule == '/portfolio' and 'GET' in rule.methods), None)}

    @app.get('/')
    def home():
        return redirect(url_for('market.index'))

    return app
