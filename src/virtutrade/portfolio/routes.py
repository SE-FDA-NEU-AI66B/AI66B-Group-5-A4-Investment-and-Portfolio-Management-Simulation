"""HTTP entry points for the portfolio page and API; no SQL or valuation here.

Two blueprints, because US06 names two paths that are not nested: the page at
`/portfolio` and the JSON endpoint at `/api/portfolio`. Both call the same
loader, so they can never disagree about what the account holds.

Identity comes from `g.current_account`, which the accounts module resolves
from the session cookie before every request. Nothing here reads an account id
from the URL, the query string or a request body.
"""

from decimal import ROUND_HALF_UP, Decimal

from flask import Blueprint, current_app, g, jsonify, render_template

from virtutrade.portfolio.errors import AccountNotFound, PortfolioDataUnavailable
from virtutrade.portfolio.service import as_api_payload, build_portfolio

blueprint = Blueprint(
    'portfolio', __name__, template_folder='templates', static_folder='static'
)
api_blueprint = Blueprint('portfolio_api', __name__)

ERROR_MESSAGES = {
    401: 'Sign in to view your portfolio.',
    404: 'This account no longer exists.',
    503: 'The portfolio is temporarily unavailable.',
}


@blueprint.app_template_filter('avg')
def average_cost(value: Decimal) -> str:
    """Display average cost to two decimals, ROUND_HALF_UP (money-rules.md).

    Display rounding never flows back into storage.
    """
    rounded = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'{rounded:,}'


def _load():
    """Shared by the page and the API. Returns (portfolio, error_code), one None."""
    account = g.get('current_account')
    if account is None:
        return None, 401
    try:
        reader = current_app.extensions['portfolio_reader_factory']()
        return build_portfolio(reader, account.id), None
    except AccountNotFound:
        current_app.logger.warning('Session names a missing account')
        return None, 404
    except PortfolioDataUnavailable:
        current_app.logger.exception('Could not load portfolio')
        return None, 503


def _private(response):
    """Holdings and cash are per-user: never let a shared cache keep them."""
    response.headers['Cache-Control'] = 'no-store'
    return response


@blueprint.get('')
def index():
    portfolio, error = _load()
    if error is not None:
        response = current_app.make_response(
            (render_template('portfolio/index.html', portfolio=None, error=error), error)
        )
        return _private(response)
    return _private(current_app.make_response(
        render_template('portfolio/index.html', portfolio=portfolio, error=None)
    ))


@api_blueprint.get('/portfolio')
def api_portfolio():
    """`GET /api/portfolio`. Internal failure text never reaches the client."""
    portfolio, error = _load()
    if error is not None:
        return _private(current_app.make_response(
            (jsonify({'error': ERROR_MESSAGES[error]}), error)
        ))
    return _private(jsonify(as_api_payload(portfolio)))