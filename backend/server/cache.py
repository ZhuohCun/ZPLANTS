from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

from flask import current_app, g, has_request_context

try:
    import redis
except Exception:
    redis = None

_client = None
_client_key = None
_unavailable_until = 0.0


def _config(config=None):
    if config is None:
        try:
            config = current_app._get_current_object().config
        except RuntimeError:
            return None
    if redis is None or not bool(config.get('REDIS_CACHE_ENABLED', True)):
        return None
    return config


def _client_settings(config):
    url = str(config.get('REDIS_URL') or '').strip()
    if url:
        return ('url', url)
    return (
        'host',
        str(config.get('REDIS_HOST', '127.0.0.1')),
        int(config.get('REDIS_PORT', 6379)),
        int(config.get('REDIS_DB', 0)),
        str(config.get('REDIS_PASSWORD') or ''),
    )


def _stats() -> dict[str, int]:
    if not has_request_context():
        return {'hits': 0, 'misses': 0, 'stores': 0, 'invalidations': 0, 'errors': 0}
    stats = getattr(g, '_redis_stats', None)
    if stats is None:
        stats = {'hits': 0, 'misses': 0, 'stores': 0, 'invalidations': 0, 'errors': 0}
        g._redis_stats = stats
    return stats


def redis_request_stats() -> dict[str, int]:
    return dict(_stats())


def _cooldown_seconds(config) -> float:
    try:
        return max(0.5, float(config.get('REDIS_FAILURE_COOLDOWN_SECONDS', 3) or 3))
    except Exception:
        return 3.0


def _mark_unavailable(config=None) -> None:
    global _client, _client_key, _unavailable_until
    _client = None
    _client_key = None
    _unavailable_until = time.monotonic() + _cooldown_seconds(config or {})
    try:
        _stats()['errors'] += 1
    except Exception:
        pass


def get_redis_client(force: bool = False):
    global _client, _client_key, _unavailable_until
    config = _config()
    if config is None:
        return None
    if force:
        _unavailable_until = 0.0
    if time.monotonic() < _unavailable_until:
        return None
    key = _client_settings(config)
    if _client is not None and _client_key == key:
        return _client
    try:
        connect_timeout = float(config.get('REDIS_CONNECT_TIMEOUT', 0.15) or 0.15)
        socket_timeout = float(config.get('REDIS_SOCKET_TIMEOUT', 0.2) or 0.2)
        if key[0] == 'url':
            client = redis.Redis.from_url(key[1], socket_connect_timeout=connect_timeout, socket_timeout=socket_timeout, decode_responses=True)
        else:
            client = redis.Redis(host=key[1], port=key[2], db=key[3], password=key[4] or None, socket_connect_timeout=connect_timeout, socket_timeout=socket_timeout, decode_responses=True)
        client.ping()
        _client = client
        _client_key = key
        return _client
    except Exception:
        _mark_unavailable(config)
        return None


def cache_prefix() -> str:
    try:
        prefix = str(current_app.config.get('REDIS_CACHE_KEY_PREFIX', 'campus-plant-suite')).strip()
    except RuntimeError:
        prefix = 'campus-plant-suite'
    return prefix.rstrip(':') or 'campus-plant-suite'


def build_cache_key(namespace: str, *parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    safe_namespace = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in str(namespace or 'cache'))
    return f'{cache_prefix()}:{safe_namespace}:{digest}'


def redis_get_json(namespace: str, *parts: Any):
    client = get_redis_client()
    if client is None:
        return False, None
    key = build_cache_key(namespace, *parts)
    try:
        payload = client.get(key)
        if payload is None:
            _stats()['misses'] += 1
            return False, None
        _stats()['hits'] += 1
        return True, json.loads(payload)
    except Exception:
        _mark_unavailable()
        return False, None


def redis_set_json(namespace: str, value: Any, ttl_seconds: int | None, *parts: Any) -> None:
    client = get_redis_client()
    if client is None:
        return
    key = build_cache_key(namespace, *parts)
    try:
        ttl = int(ttl_seconds or current_app.config.get('REDIS_CACHE_TTL_SECONDS', 120) or 120)
        ttl = max(1, ttl)
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str, separators=(',', ':')))
        _stats()['stores'] += 1
    except Exception:
        _mark_unavailable()


def redis_remember_json(namespace: str, parts: tuple[Any, ...], ttl_seconds: int, producer: Callable[[], Any]):
    hit, value = redis_get_json(namespace, *parts)
    if hit:
        return value
    value = producer()
    redis_set_json(namespace, value, ttl_seconds, *parts)
    return value


def redis_delete_namespace(namespace: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    safe_namespace = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in str(namespace or 'cache'))
    pattern = f'{cache_prefix()}:{safe_namespace}:*'
    deleted = 0
    batch = []
    try:
        for key in client.scan_iter(match=pattern, count=200):
            batch.append(key)
            if len(batch) >= 200:
                deleted += int(client.delete(*batch) or 0)
                batch.clear()
        if batch:
            deleted += int(client.delete(*batch) or 0)
        _stats()['invalidations'] += deleted
    except Exception:
        _mark_unavailable()


def invalidate_namespaces(*namespaces: str) -> None:
    for namespace in namespaces:
        redis_delete_namespace(namespace)


def redis_cache_status() -> dict:
    config = _config()
    if config is None:
        return {'enabled': False, 'reachable': False, 'detail': 'Redis caching is disabled or the redis client is unavailable.'}
    client = get_redis_client(force=True)
    base = {
        'enabled': True,
        'required': False,
        'host': config.get('REDIS_HOST', '127.0.0.1'),
        'port': int(config.get('REDIS_PORT', 6379) or 6379),
        'db': int(config.get('REDIS_DB', 0) or 0),
        'keyPrefix': cache_prefix(),
        'defaultTtlSeconds': int(config.get('REDIS_CACHE_TTL_SECONDS', 120) or 120),
    }
    if client is None:
        return {**base, 'reachable': False, 'detail': 'Redis is not reachable. Business APIs will use MySQL or external services directly.'}
    try:
        return {**base, 'reachable': bool(client.ping()), 'detail': 'Redis is used only for selected repeated-read and external-lookup caches.'}
    except Exception:
        _mark_unavailable(config)
        return {**base, 'reachable': False, 'detail': 'Redis ping failed. Business APIs will use MySQL or external services directly.'}
