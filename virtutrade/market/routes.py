"""HTTP entry points for the market page; no SQL or provider calls here."""

import sqlite3

from flask import Blueprint, current_app, render_template

from virtutrade.market.service import market_snapshot

blueprint = Blueprint('market', __name__, template_folder='templates', static_folder='static')


@blueprint.app_template_filter('vnd')
def vnd(value):
    return f'{value:,}'


@blueprint.get('')
def index():
    try:
        quotes = market_snapshot(current_app.config['DATABASE'])
    except sqlite3.Error:
        current_app.logger.exception('Could not read market database')
        return render_template('market/index.html', quotes=[], error=True), 503
    return render_template('market/index.html', quotes=quotes, error=False)
