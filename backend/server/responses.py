from datetime import datetime
import re
from flask import jsonify


def now_string():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


_DATETIME_PATTERNS = (
    re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'),
    re.compile(r'^\d{4}-\d{2}-\d{2}$'),
    re.compile(r'^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$'),
)

_MONTH_ABBR = ('Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.', 'Jul.', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.')


def to_display_datetime(value):
    if isinstance(value, datetime):
        return f"{_MONTH_ABBR[value.month - 1]} {value.day}, {value.year} {value:%H:%M:%S}"
    text = str(value or '').strip()
    if not text:
        return ''
    normalized = text.replace('T', ' ').replace('Z', '')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%a, %d %b %Y %H:%M:%S GMT'):
        try:
            dt = datetime.strptime(normalized if fmt != '%a, %d %b %Y %H:%M:%S GMT' else text, fmt)
            if fmt == '%Y-%m-%d':
                return f"{_MONTH_ABBR[dt.month - 1]} {dt.day}, {dt.year}"
            return f"{_MONTH_ABBR[dt.month - 1]} {dt.day}, {dt.year} {dt:%H:%M:%S}"
        except Exception:
            continue
    return text


def _normalize_payload(value):
    if isinstance(value, dict):
        return {key: _normalize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_payload(item) for item in value]
    if isinstance(value, datetime):
        return to_display_datetime(value)
    if isinstance(value, str) and any(pattern.fullmatch(value.strip()) for pattern in _DATETIME_PATTERNS):
        return to_display_datetime(value)
    return value


def success(data=None, msg='Done', http_status=200):
    body = {'code': 0, 'msg': msg, 'data': _normalize_payload(data if data is not None else {})}
    return jsonify(body), http_status


def fail(code=500, msg='The action could not be completed.', http_status=200, data=None):
    body = {'code': code, 'msg': msg, 'data': _normalize_payload(data if data is not None else {})}
    return jsonify(body), http_status
