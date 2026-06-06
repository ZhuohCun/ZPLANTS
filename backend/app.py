
from server import create_app

app = create_app()


def _serve_backend_app():
    from waitress import serve

    serve(
        app,
        host=app.config['BACKEND_HOST'],
        port=app.config['BACKEND_PORT'],
        threads=app.config['BACKEND_THREADS'],
        backlog=app.config['BACKEND_BACKLOG'],
        channel_timeout=app.config['BACKEND_CHANNEL_TIMEOUT'],
        cleanup_interval=app.config['BACKEND_CLEANUP_INTERVAL']
    )


if __name__ == '__main__':
    _serve_backend_app()
