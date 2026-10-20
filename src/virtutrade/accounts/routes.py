"""HTTP entry points: HTML pages plus the JSON auth API from the contract.

API paths (/api/*) speak strict JSON; page paths speak HTML forms. Both share
the service layer. Every state-changing request needs CSRF: pre-auth tokens
for login/register, session-bound tokens afterwards.
"""
from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request
from werkzeug.exceptions import BadRequest

from virtutrade.accounts import errors, service

blueprint = Blueprint('accounts', __name__, template_folder='templates')

SESSION_COOKIE = 'vt_session'
SESSION_MAX_AGE = 12 * 3600
UI_ERROR_HINTS = {
    'EMAIL_IN_USE': 'Sign in with this email, or register with another one.',
    'INVALID_CREDENTIALS': 'Check both fields and try again.',
    'LOGIN_LOCKED': 'You can sign in again when the countdown ends.',
    'CSRF_FAILED': 'Reload the page and try again.',
    'ACCOUNT_DISABLED': 'This account is disabled and cannot be used to sign in or trade.',
}


def init_auth(app):
    """Load the current account for templates and expose the callbacks the
    future order module needs (see PR #92 handoff doc). Never breaks public
    pages: any auth failure simply means guest."""

    @app.before_request
    def load_current_account():
        g.current_account = None
        g.current_session_id = None
        g.csrf_token = None
        token = request.cookies.get(SESSION_COOKIE, '')
        if not token:
            return
        try:
            account, session_id = service.resolve_with_id(
                current_app.config['DATABASE'], session_token=token)
        except errors.AuthError:
            return
        g.current_account = account
        g.current_session_id = session_id
        g.csrf_token = service.mint_csrf(
            current_app.config['SECRET_KEY'], session_id)

    app.extensions['orders_identity'] = require_order_session
    app.extensions['orders_csrf_token'] = current_order_csrf_token


def require_order_session(incoming_request):
    """PR #92 integration: return the internal auth_session id for a valid
    request, else raise the matching auth error for the caller to translate."""
    config = current_app.config
    token = incoming_request.cookies.get(SESSION_COOKIE, '')
    _account, session_id = service.resolve_with_id(
        config['DATABASE'], session_token=token)
    _check_origin()
    csrf = (incoming_request.headers.get('X-CSRF-Token')
            or incoming_request.form.get('csrf_token', ''))
    if not service.valid_csrf(config['SECRET_KEY'], session_id, csrf):
        raise errors.CsrfFailed()
    return session_id


def current_order_csrf_token():
    session_id = g.get('current_session_id')
    if session_id is None:
        raise errors.AuthRequired()
    return service.mint_csrf(current_app.config['SECRET_KEY'], session_id)


@blueprint.after_request
def no_store(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def _is_api():
    return request.path.startswith('/api/')


def _envelope(exc):
    return {'error': {'code': exc.code, 'message': exc.message,
                      'details': exc.details}}


def _fail(exc):
    if _is_api():
        response = jsonify(_envelope(exc))
        response.status_code = exc.status
        if isinstance(exc, errors.AccountLocked):
            response.headers['Retry-After'] = str(exc.retry_after)
        return response
    token = service.mint_preauth_csrf(current_app.config['SECRET_KEY'])
    page = ('accounts/login.html' if 'login' in request.path
            else 'accounts/register.html')
    return render_template(page, error=exc.message, error_code=exc.code,
                           error_hint=UI_ERROR_HINTS.get(exc.code), csrf_token=token,
                           email=request.form.get('email', '')), exc.status


def _check_origin():
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    if not service.same_origin_ok(request.host, origin, referer):
        raise errors.CsrfFailed()


def _submitted_csrf():
    return (request.headers.get('X-CSRF-Token')
            or request.form.get('csrf_token', ''))


def _check_preauth_csrf():
    if not service.valid_preauth_csrf(current_app.config['SECRET_KEY'],
                                      _submitted_csrf()):
        raise errors.CsrfFailed()


def _credentials_from_request():
    if _is_api():
        if not request.is_json:
            raise errors.UnsupportedMedia()
        try:
            payload = request.get_json(force=False)
        except BadRequest:
            raise errors.InvalidJson()
        if not isinstance(payload, dict):
            raise errors.InvalidJson()
        email = payload.get('email')
        password = payload.get('password')
    else:
        email = request.form.get('email', '')
        password = request.form.get('password', '')
    if email is None or password is None:
        raise errors.ValidationError('Email and password are required.')
    return email, password


def _set_session_cookie(response, token):
    response.set_cookie(SESSION_COOKIE, token, httponly=True,
                        samesite='Lax', path='/', max_age=SESSION_MAX_AGE,
                        secure=request.is_secure)
    return response


def _expire_session_cookie(response):
    response.set_cookie(SESSION_COOKIE, '', httponly=True, samesite='Lax',
                        path='/', expires=0, max_age=0)
    return response


def _do_register():
    try:
        _check_origin()
        _check_preauth_csrf()
        email, password = _credentials_from_request()
        account, token, _session = service.register(
            current_app.config['DATABASE'], email=email, password=password)
    except errors.AuthError as exc:
        return _fail(exc)
    if _is_api():
        response = jsonify({'account': {'id': account.id, 'email': account.email,
                                        'role': account.role,
                                        'cash_vnd': account.cash_vnd},
                            'redirect_to': '/portfolio'})
        response.status_code = 201
        response.headers['Location'] = '/api/portfolio'
        return _set_session_cookie(response, token)
    return _set_session_cookie(redirect('/market'), token)


def _post_login_destination():
    """US01-AC2: reach the portfolio once #81 registers it; market until then."""
    if any(rule.rule == '/portfolio' and 'GET' in rule.methods
           for rule in current_app.url_map.iter_rules()):
        return '/portfolio'
    return '/market'


def _do_login():
    try:
        _check_origin()
        _check_preauth_csrf()
        email, password = _credentials_from_request()
        account, token, _session = service.authenticate(
            current_app.config['DATABASE'], email=email, password=password)
    except errors.AuthError as exc:
        return _fail(exc)
    if _is_api():
        response = jsonify({'account': {'id': account.id, 'role': account.role},
                            'redirect_to': '/portfolio'})
        return _set_session_cookie(response, token)
    return _set_session_cookie(redirect(_post_login_destination()), token)


def _do_logout():
    session = service.find_session(
        current_app.config['DATABASE'],
        session_token=request.cookies.get(SESSION_COOKIE, ''))
    if session is None:
        exc = errors.AuthRequired()
        if _is_api():
            return jsonify(_envelope(exc)), exc.status
        return redirect('/login')
    if not service.valid_csrf(current_app.config['SECRET_KEY'], session.id,
                              _submitted_csrf()):
        exc = errors.CsrfFailed()
        if _is_api():
            return jsonify(_envelope(exc)), exc.status
        return redirect('/login')
    try:
        service.logout(current_app.config['DATABASE'],
                       session_token=request.cookies.get(SESSION_COOKIE, ''))
    except errors.AuthError as exc:
        if _is_api():
            return jsonify(_envelope(exc)), exc.status
        return redirect('/login')
    if _is_api():
        return _expire_session_cookie(
            current_app.response_class(status=204))
    return _expire_session_cookie(redirect('/market'))


@blueprint.get('/register')
def register_page():
    token = service.mint_preauth_csrf(current_app.config['SECRET_KEY'])
    return render_template('accounts/register.html', error=None, error_code=None,
                           error_hint=None,
                           csrf_token=token, email='')


@blueprint.post('/register')
@blueprint.post('/api/accounts')
def register():
    return _do_register()


@blueprint.get('/login')
def login_page():
    token = service.mint_preauth_csrf(current_app.config['SECRET_KEY'])
    return render_template('accounts/login.html', error=None, error_code=None,
                           error_hint=None,
                           csrf_token=token, email='')


@blueprint.post('/login')
@blueprint.post('/api/sessions')
def login():
    return _do_login()


@blueprint.post('/logout')
@blueprint.delete('/api/sessions/current')
def logout():
    return _do_logout()
