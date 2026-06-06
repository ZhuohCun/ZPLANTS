
from __future__ import annotations

import pymysql
from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


_engine = None
_engine_key = None


def _normalized_sql(sql: str) -> str:
    return ' '.join(str(sql or '').strip().split()).lower()


def _is_mutating_sql(sql: str) -> bool:
    text = _normalized_sql(sql)
    return text.startswith(('insert ', 'update ', 'delete ', 'replace ', 'alter ', 'drop ', 'create ', 'truncate '))


class Database:
    def __init__(self, connection):
        self.connection = connection
        self.supports_named_locks = True

    def _cursor(self):
        return self.connection.cursor(pymysql.cursors.DictCursor)

    def execute(self, sql, params=None):
        cursor = self._cursor()
        cursor.execute(sql.replace('?', '%s'), params or ())
        return cursor

    def executemany(self, sql, params_list):
        cursor = self._cursor()
        cursor.executemany(sql.replace('?', '%s'), params_list)

    def fetchone(self, sql, params=None):
        cursor = self.execute(sql, params or ())
        try:
            return cursor.fetchone()
        finally:
            cursor.close()

    def fetchall(self, sql, params=None):
        cursor = self.execute(sql, params or ())
        try:
            return cursor.fetchall() or []
        finally:
            cursor.close()

    def begin(self):
        self.connection.begin()

    def scalar(self, sql, params=None, default=None):
        row = self.fetchone(sql, params)
        if not row:
            return default
        return next(iter(row.values()), default)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def _config_value(app, primary, fallback=None, default=None):
    if primary in app.config:
        return app.config[primary]
    if fallback and fallback in app.config:
        return app.config[fallback]
    return default


def build_engine(app):
    global _engine, _engine_key
    db_host = _config_value(app, 'DB_HOST', 'MYSQL_HOST', '127.0.0.1')
    db_port = int(_config_value(app, 'DB_PORT', 'MYSQL_PORT', 3306))
    db_user = _config_value(app, 'DB_USER', 'MYSQL_USER', 'root')
    db_password = _config_value(app, 'DB_PASSWORD', 'MYSQL_PASSWORD', '')
    db_name = _config_value(app, 'DB_NAME', 'MYSQL_DATABASE', 'Plants_Recognition')
    db_charset = _config_value(app, 'MYSQL_CHARSET', None, 'utf8mb4')
    engine_key = (db_host, db_port, db_user, db_password, db_name, db_charset)
    if _engine is not None and _engine_key == engine_key:
        return _engine
    url = URL.create(
        drivername='mysql+pymysql',
        username=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=db_name,
        query={'charset': db_charset},
    )
    _engine = create_engine(
        url,
        pool_pre_ping=bool(app.config.get('MYSQL_POOL_PRE_PING', True)),
        pool_recycle=int(app.config.get('MYSQL_POOL_RECYCLE', 1800)),
        pool_size=int(app.config.get('MYSQL_POOL_SIZE', 12)),
        max_overflow=int(app.config.get('MYSQL_MAX_OVERFLOW', -1)),
        pool_timeout=int(app.config.get('MYSQL_POOL_TIMEOUT', 60)),
        future=True,
        connect_args={
            'connect_timeout': int(app.config.get('MYSQL_CONNECT_TIMEOUT', 5)),
            'read_timeout': int(app.config.get('MYSQL_READ_TIMEOUT', 30)),
            'write_timeout': int(app.config.get('MYSQL_WRITE_TIMEOUT', 30)),
        },
    )
    _engine_key = engine_key
    return _engine


def get_db():
    if 'db' not in g:
        raw_conn = build_engine(current_app).raw_connection()
        g.db = Database(raw_conn)
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
