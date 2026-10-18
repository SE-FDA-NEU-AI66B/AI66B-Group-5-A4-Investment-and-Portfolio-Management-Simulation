"""Domain failures with their API contract codes and HTTP statuses."""


class AuthError(Exception):
    code = 'AUTH_ERROR'
    status = 500
    message = 'Authentication error'

    def __init__(self, message=None, details=None, retry_after=None):
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        self.details = details or {}
        self.retry_after = retry_after


class EmailInUse(AuthError):
    code = 'EMAIL_IN_USE'
    status = 409
    message = 'Email already in use'


class InvalidCredentials(AuthError):
    code = 'INVALID_CREDENTIALS'
    status = 401
    message = 'Invalid email or password'


class AccountLocked(AuthError):
    code = 'LOGIN_LOCKED'
    status = 429

    def __init__(self, retry_after_seconds):
        super().__init__(
            f'Account locked. Try again in {retry_after_seconds} seconds.',
            details={'retry_after_seconds': retry_after_seconds},
            retry_after=retry_after_seconds,
        )


class AccountDisabled(AuthError):
    code = 'ACCOUNT_DISABLED'
    status = 403
    message = 'Account is disabled'


class AuthRequired(AuthError):
    code = 'AUTH_REQUIRED'
    status = 401
    message = 'Authentication required'


class CsrfFailed(AuthError):
    code = 'CSRF_FAILED'
    status = 403
    message = 'Invalid or missing CSRF token'


class ValidationError(AuthError):
    code = 'VALIDATION_ERROR'
    status = 422


class InvalidJson(AuthError):
    code = 'INVALID_JSON'
    status = 400
    message = 'Malformed JSON body'


class UnsupportedMedia(AuthError):
    code = 'UNSUPPORTED_MEDIA_TYPE'
    status = 415
    message = 'Content-Type must be application/json'
