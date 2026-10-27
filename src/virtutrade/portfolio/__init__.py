"""Portfolio page module: routes, presentation, queries, templates and assets."""

from virtutrade.portfolio.routes import api_blueprint as api_blueprint
from virtutrade.portfolio.routes import blueprint as blueprint

__all__ = ['api_blueprint', 'blueprint']