"""HTTP entry points for the market page; no SQL or provider calls here."""

from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, render_template, request

from virtutrade.market.errors import MarketDataUnavailable
from virtutrade.market.service import (
    VIETNAM,
    filter_quotes,
    find_quote,
    market_snapshot,
    normalize_query,
    parse_timestamp,
)

api_blueprint = Blueprint('market_api', __name__)

blueprint = Blueprint('market', __name__, template_folder='templates', static_folder='static')

SOURCE_LABELS = {'seed': 'Demo / seed', 'simulation': 'Simulation / generated'}

@blueprint.app_template_filter('vnd')
def vnd(value):
    return f'{value:,}'


@blueprint.app_template_filter('local_time')
def local_time(value):
    """Show a stored UTC timestamp in Vietnam time with an explicit zone label."""
    try:
        moment = parse_timestamp(value).astimezone(VIETNAM)
    except (ValueError, TypeError, AttributeError):
        return value
    return moment.strftime('%H:%M:%S %d/%m/%Y') + ' (UTC+7)'


@blueprint.app_template_filter('source_label')
def source_label(value):
    return SOURCE_LABELS.get(value, 'DNSE')


def load_quotes():
    reader = current_app.extensions['market_reader_factory']()
    return market_snapshot(reader)


def quote_payload(quote):
    """Keep list and detail JSON on one public quote representation."""
    value = asdict(quote)
    value['change'] = None if quote.change is None else format(quote.change, '.2f')
    return value


@blueprint.get('')
def index():
    query = normalize_query(request.args.get('q'))
    try:
        all_quotes = load_quotes()
    except MarketDataUnavailable:
        current_app.logger.exception('Could not load market snapshot')
        return render_template('market/index.html', quotes=[], total=0, query=query, error=True), 503
    return render_template('market/index.html', quotes=filter_quotes(all_quotes, query), total=len(all_quotes), query=query, error=False)


@blueprint.get('/<symbol>')
def detail(symbol):
    symbol = symbol.strip().upper()[:20]
    try:
        quote = find_quote(load_quotes(), symbol)
    except MarketDataUnavailable:
        current_app.logger.exception('Could not load market snapshot')
        return render_template('market/detail.html', quote=None, symbol=symbol, error=True), 503
    if quote is None:
        return render_template('market/detail.html', quote=None, symbol=symbol, error=False), 404
    return render_template('market/detail.html', quote=quote, symbol=symbol, error=False)


@api_blueprint.get('/quotes')
def quotes_json():
    query = normalize_query(request.args.get('q'))
    try:
        response = jsonify(quotes=[quote_payload(quote) for quote in filter_quotes(load_quotes(), query)])
    except MarketDataUnavailable:
        response = jsonify(error={
            'code': 'MARKET_UNAVAILABLE',
            'message': 'Market data is temporarily unavailable. Try again.',
            'details': {}
        })
        response.status_code = 503
    response.headers['Cache-Control'] = 'no-store'
    return response


@api_blueprint.get('/quotes/<symbol>')
def quote_json(symbol):
    symbol = symbol.strip().upper()[:20]
    try:
        quote = find_quote(load_quotes(), symbol)
    except MarketDataUnavailable:
        response = jsonify(error={
            'code': 'QUOTE_UNAVAILABLE',
            'message': 'Quote data is temporarily unavailable. Try again.',
            'details': {},
        })
        response.status_code = 503
    else:
        if quote is None:
            response = jsonify(error={
                'code': 'TICKER_NOT_FOUND',
                'message': 'Ticker not found',
                'details': {'symbol': symbol},
            })
            response.status_code = 404
        else:
            response = jsonify(quote=quote_payload(quote))
    response.headers['Cache-Control'] = 'no-store'
    return response
