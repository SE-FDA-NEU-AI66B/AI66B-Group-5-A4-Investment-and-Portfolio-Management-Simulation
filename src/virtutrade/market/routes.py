"""HTTP entry points for the market page; no SQL or provider calls here."""

from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, render_template

from virtutrade.market.errors import MarketDataUnavailable
from virtutrade.market.service import market_snapshot

api_blueprint = Blueprint('market_api', __name__)

blueprint = Blueprint('market', __name__, template_folder='templates', static_folder='static')


@blueprint.app_template_filter('vnd')
def vnd(value):
    return f'{value:,}'


@blueprint.get('')
def index():
    try:
        reader = current_app.extensions['market_reader_factory']()
        quotes = market_snapshot(reader)
    except MarketDataUnavailable:
        current_app.logger.exception('Could not load market snapshot')
        return render_template('market/index.html', quotes=[], error=True), 503
    return render_template('market/index.html', quotes=quotes, error=False)


@api_blueprint.get('/quotes')
def quotes_json():
    try:
        reader = current_app.extensions['market_reader_factory']()
        quotes = []
        for quote in market_snapshot(reader):
            value = asdict(quote)
            value['change'] = None if quote.change is None else format(quote.change, '.2f')
            quotes.append(value)
        response = jsonify(quotes=quotes)
    except MarketDataUnavailable:
        response = jsonify(error={'code': 'MARKET_UNAVAILABLE',
                                  'message': 'Market data is temporarily unavailable. Try again.',
                                  'details': {}})
        response.status_code = 503
    response.headers['Cache-Control'] = 'no-store'
    return response
