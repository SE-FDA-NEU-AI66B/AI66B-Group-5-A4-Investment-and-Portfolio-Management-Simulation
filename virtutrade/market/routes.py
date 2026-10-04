"""HTTP entry points for the market page; no SQL or provider calls here."""

from flask import Blueprint, current_app, render_template

from virtutrade.market.errors import MarketDataUnavailable
from virtutrade.market.service import market_snapshot

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
