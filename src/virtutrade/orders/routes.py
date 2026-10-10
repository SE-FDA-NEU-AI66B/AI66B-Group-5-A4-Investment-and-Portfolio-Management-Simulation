"""Buy UI and API. Fail closed until #77 installs the trusted auth adapter."""

from functools import partial

from flask import Blueprint, current_app, jsonify, render_template, request

from virtutrade.orders.errors import OrderError
from virtutrade.orders.repository import order_unit_of_work
from virtutrade.orders.service import execute_buy, preview_order

blueprint = Blueprint(
    "orders",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/trade/static",
)
STATUS = {
    "AUTH_REQUIRED": 401,
    "ACCOUNT_DISABLED": 403,
    "CSRF_FAILED": 403,
    "TICKER_NOT_FOUND": 404,
    "QUOTE_STALE": 409,
    "QUOTE_CHANGED": 409,
    "INSUFFICIENT_CASH": 409,
    "INVALID_QUANTITY": 422,
    "VALIDATION_ERROR": 422,
    "QUOTE_UNAVAILABLE": 503,
    "SERVICE_UNAVAILABLE": 503,
    "INVALID_JSON": 400,
    "UNSUPPORTED_MEDIA_TYPE": 415,
}
STATUS.update(SIMULATION_DISABLED=403, SIMULATION_CLOCK_NOT_ADVANCED=409)


def identity():
    # Contract: auth adapter verifies session and, for POST, same-origin + CSRF.
    # It returns an internal auth_session.id, never a browser-supplied account ID.
    resolver = current_app.extensions.get("orders_identity")
    if resolver is None:
        raise OrderError(
            "SERVICE_UNAVAILABLE",
            "Trading is temporarily unavailable. Please try again later.",
        )
    session_id = resolver(request)
    if type(session_id) is not int or session_id <= 0:
        raise OrderError("AUTH_REQUIRED", "Sign in before trading.")
    return session_id


def payload(fields):
    if not request.is_json:
        raise OrderError("UNSUPPORTED_MEDIA_TYPE", "Send the form as JSON.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise OrderError(
            "INVALID_JSON",
            "The request could not be read. Reload the form and try again.",
        )
    if set(data) != set(fields):
        raise OrderError(
            "VALIDATION_ERROR", "Check the required order fields and preview again."
        )
    return data


@blueprint.errorhandler(OrderError)
def error_response(error):
    response = jsonify(
        error={"code": error.code, "message": error.message, "details": error.details}
    )
    response.status_code = STATUS[error.code]
    return response


@blueprint.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@blueprint.get("/trade")
def trade_form():
    # Public shell does not expose balances; every read/write API checks identity.
    token_provider = current_app.extensions.get("orders_csrf_token")
    return render_template(
        "orders/trade.html",
        symbol=request.args.get("symbol", ""),
        csrf_token=token_provider() if token_provider else "",
        simulation=current_app.config.get("QUOTE_MODE") == "simulation",
        auth_ready="orders_identity" in current_app.extensions,
    )


@blueprint.post("/api/orders/preview")
def preview():
    session_id = identity()
    data = payload(["side", "symbol", "quantity"])
    result = preview_order(
        session_id,
        **data,
        unit_of_work=partial(order_unit_of_work, current_app.config["DATABASE"]),
    )
    return jsonify(result)


@blueprint.post("/api/orders/buy")
def buy():
    session_id = identity()
    data = payload(["symbol", "quantity", "expected_quote_at"])
    result = execute_buy(
        session_id,
        **data,
        unit_of_work=partial(order_unit_of_work, current_app.config["DATABASE"]),
    )
    return jsonify(result), 201


@blueprint.post("/api/simulation/quotes/refresh")
def refresh_simulation():
    from virtutrade.simulation.repository import simulation_unit_of_work
    from virtutrade.simulation.service import refresh_quotes

    session_id = identity()
    payload([])
    if current_app.config.get("QUOTE_MODE") != "simulation":
        raise OrderError(
            "SIMULATION_DISABLED",
            "Demo generation is unavailable in this mode. Use the local simulation setup.",
        )
    return jsonify(
        refresh_quotes(
            session_id, partial(simulation_unit_of_work, current_app.config["DATABASE"])
        )
    )
