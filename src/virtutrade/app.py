"""Application factory: configure Flask and register each feature module."""

import os
import sqlite3

from flask import Flask, jsonify, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from virtutrade.accounts import blueprint as accounts_blueprint
from virtutrade.accounts.routes import init_auth
from virtutrade.config import load_config
from virtutrade.market import blueprint as market_blueprint
from virtutrade.market.repository import SQLiteQuoteRepository
from virtutrade.market.routes import api_blueprint
from virtutrade.orders.routes import blueprint as orders_blueprint
from virtutrade.portfolio import api_blueprint as portfolio_api_blueprint
from virtutrade.portfolio import blueprint as portfolio_blueprint
from virtutrade.portfolio.repository import SQLitePortfolioRepository


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(load_config())
    if config:
        app.config.update(config)
    if app.config.get('TRUST_PROXY'):
        # Public scheme/host from the proxy keep Secure cookies and the origin check right.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    # Compose infrastructure here; controllers/services do not select a database.
    app.extensions['market_reader_factory'] = lambda: SQLiteQuoteRepository(
        app.config['DATABASE'], provider_only=app.config.get('QUOTE_MODE') == 'dnse')
    app.extensions['portfolio_reader_factory'] = (
        lambda: SQLitePortfolioRepository(app.config['DATABASE'])
    )
    app.register_blueprint(accounts_blueprint)
    app.register_blueprint(market_blueprint, url_prefix='/market')
    app.register_blueprint(api_blueprint, url_prefix='/api/market')
    app.register_blueprint(orders_blueprint)
    app.register_blueprint(portfolio_blueprint, url_prefix='/portfolio')
    app.register_blueprint(portfolio_api_blueprint, url_prefix='/api')
    init_auth(app)

    @app.context_processor
    def feature_navigation():
        # Long owns /portfolio. Expose a link only when the real GET route lands.
        return {'portfolio_url': next((rule.rule for rule in app.url_map.iter_rules()
                                       if rule.rule == '/portfolio' and 'GET' in rule.methods), None)}

    @app.get('/')
    def home():
        return redirect(url_for('market.index'))

    @app.get('/health')
    def health():
        """200 when the database answers and holds quotes, 503 otherwise.

        Never reveals paths, settings or account data; the commit lets a
        reviewer match the running build to the v1.0 tag.
        """
        from virtutrade.database.health import quote_count
        commit = (os.environ.get('RENDER_GIT_COMMIT') or os.environ.get('GIT_COMMIT') or '')[:7]
        try:
            quotes = quote_count(app.config['DATABASE'])
        except sqlite3.Error as exc:
            app.logger.warning('Health check failed: database unavailable (%s)', type(exc).__name__)
            quotes = None
        healthy = bool(quotes)
        response = jsonify(status='ok' if healthy else 'unavailable',
                           database='ok' if healthy else 'unavailable' if quotes is None else 'empty',
                           quotes=quotes, mode=app.config.get('QUOTE_MODE'), commit=commit or None)
        response.status_code = 200 if healthy else 503
        response.headers['Cache-Control'] = 'no-store'
        return response

    return app