from __future__ import annotations

from threading import Thread, Lock
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import requests
from flask import current_app, request

from server.db import get_db
from server.responses import now_string
from server.security import get_client_ip
from server.cache import redis_get_json, redis_set_json

_location_cache = {}
_cache_lock = Lock()


def _request_ip():
    return get_client_ip()


def _clean_lookup_ip(ip_text: str) -> str:
    text = str(ip_text or '').strip()
    if not text:
        return ''


    if ',' in text:
        text = text.split(',', 1)[0].strip()
    return text


def _build_lookup_url(ip_text: str) -> str:
    template = str(current_app.config.get('IP_LOOKUP_URL') or '').strip()
    raw_ip = _clean_lookup_ip(ip_text)
    if not template or not raw_ip:
        return ''

    encoded_ip = quote(raw_ip, safe='')
    if '{ip}' in template:
        return template.replace('{ip}', encoded_ip)


    if template.endswith(('=', '/', '?', '&')):
        return f'{template}{encoded_ip}'

    parts = urlsplit(template)
    if not parts.scheme or not parts.netloc:
        return ''

    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    for index in range(len(query_pairs) - 1, -1, -1):
        key, value = query_pairs[index]
        if value == '':
            query_pairs[index] = (key, raw_ip)
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_pairs), parts.fragment))

    return ''


def _write_location_result(log_id: int, old_status: str, location: str) -> None:
    try:
        db = get_db()
        db.execute('update operation_logs set ip_location = ? where id = ? and ip_location = ?', (location, log_id, old_status))
        db.commit()
    except Exception:
        pass


def _resolve_location_once(app, log_id: int, ip_text: str) -> None:
    with app.app_context():
        resolving_text = 'Resolving'
        timeout_text = 'Location lookup failed (timeout)'
        failed_text = 'Location lookup failed (service error)'
        empty_text = 'Location lookup failed (empty result)'
        not_configured_text = 'Location lookup failed (not configured)'
        lookup_succeeded = False
        location = failed_text
        try:
            timeout = float(app.config.get('IP_LOOKUP_TIMEOUT', 3.0) or 3.0)
        except Exception:
            timeout = 3.0
        try:
            lookup_url = _build_lookup_url(ip_text)
            if not lookup_url:
                location = not_configured_text
            else:
                response = requests.get(lookup_url, timeout=timeout)
                response.raise_for_status()
                returned_text = (response.text or '').strip()
                if returned_text:
                    location = returned_text
                    lookup_succeeded = True
                else:
                    location = empty_text
        except requests.Timeout:
            location = timeout_text
        except requests.RequestException:
            location = failed_text
        except Exception:
            location = failed_text

        if lookup_succeeded:
            with _cache_lock:
                _location_cache[ip_text] = location
            redis_set_json('ip_location', location, 60 * 60 * 24, ip_text)
        _write_location_result(log_id, resolving_text, location)


def _schedule_ip_location_lookup(log_id: int, ip_text: str) -> None:
    if not ip_text or not current_app.config.get('IP_LOOKUP_ENABLED', True):
        return
    with _cache_lock:
        cached = _location_cache.get(ip_text)
    if cached:
        try:
            db = get_db()
            db.execute('update operation_logs set ip_location = ? where id = ?', (cached, log_id))
            db.commit()
        except Exception:
            pass
        return
    hit, cached = redis_get_json('ip_location', ip_text)
    if hit and cached:
        with _cache_lock:
            _location_cache[ip_text] = cached
        try:
            db = get_db()
            db.execute('update operation_logs set ip_location = ? where id = ?', (cached, log_id))
            db.commit()
        except Exception:
            pass
        return
    app = current_app._get_current_object()
    Thread(target=_resolve_location_once, args=(app, log_id, ip_text), name=f'ip-location-{log_id}', daemon=True).start()


def append_log(user, operation_name, request_url=None, method=None, module_id=None, extra_remark=''):
    db = get_db()
    operator_id = user.get('id') if isinstance(user, dict) else None
    operation_text = str(operation_name or '').strip()
    remark_text = str(extra_remark or '').strip()
    if remark_text:
        operation_text = f'{operation_text}({remark_text})'
    ip_text = _request_ip()
    initial_location = 'Resolving' if current_app.config.get('IP_LOOKUP_ENABLED', True) and ip_text else ''
    cursor = db.execute(
        'insert into operation_logs (user_id, module_id, operation_name, request_url, request_method, ip, ip_location, create_time) values (?, ?, ?, ?, ?, ?, ?, ?)',
        (operator_id, module_id, operation_text, request_url or request.path, method or request.method, ip_text, initial_location, now_string()),
    )
    try:
        db.commit()
    except Exception:
        pass
    try:
        _schedule_ip_location_lookup(cursor.lastrowid, ip_text)
    except Exception:
        pass


def init_ip_location_service(app=None):
    pass
