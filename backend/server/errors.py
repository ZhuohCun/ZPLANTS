from werkzeug.exceptions import HTTPException
from flask import current_app
from server.responses import fail


class ApiError(Exception):
    def __init__(self, code, message, status=400, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.data = data


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return fail(error.code, error.message, error.status, error.data)


    @app.errorhandler(400)
    def handle_bad_request(error):
        return fail(400, 'The submitted information is incomplete or invalid.', 400)

    @app.errorhandler(401)
    def handle_unauthorized(error):
        return fail(401, 'Please sign in again.', 401)

    @app.errorhandler(403)
    def handle_forbidden(error):
        return fail(403, 'You do not have access to this feature.', 403)

    @app.errorhandler(404)
    def handle_not_found(error):
        return fail(404, 'The requested item was not found.', 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return fail(405, 'This action is not available here.', 405)

    @app.errorhandler(413)
    def handle_too_large(error):
        return fail(413, 'The uploaded file is too large.', 413)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return fail(error.code or 500, error.description or 'The service is temporarily unavailable.', error.code or 500)
        current_app.logger.exception('unhandled exception', exc_info=error)
        return fail(500, 'The service could not complete the request.', 500)
