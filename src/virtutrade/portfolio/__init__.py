"""Portfolio page module: routes, presentation, queries, templates and assets."""

from virtutrade.portfolio.routes import api_blueprint as api_blueprint
from virtutrade.portfolio.routes import blueprint as blueprint
from virtutrade.portfolio.routes import history_blueprint as history_blueprint

__all__ = ['api_blueprint', 'blueprint', 'history_blueprint']
