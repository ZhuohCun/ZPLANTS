
import base64
import hashlib
import hmac
from ipaddress import ip_address, ip_network

import jwt
from flask import current_app, request
from werkzeug.security import check_password_hash
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from config import parse_csv_text

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.heif', '.hif'}

_private_password_key_cache = {'base64': None, 'key': None}


def _load_password_private_key():
    base64_text = str(current_app.config.get('PASSWORD_RSA_PRIVATE_KEY_BASE64') or '')
    if not base64_text:
        raise ValueError('The password transport private key is missing.')
    if _private_password_key_cache['base64'] != base64_text:
        try:
            der_bytes = base64.b64decode(base64_text.encode('ascii'), validate=True)
        except Exception as exc:
            raise ValueError('The password transport private key must be a continuous Base64 key body.') from exc
        _private_password_key_cache['key'] = serialization.load_der_private_key(
            der_bytes,
            password=None,
        )
        _private_password_key_cache['base64'] = base64_text
    return _private_password_key_cache['key']


def decrypt_password_transport_value(encrypted_value: str, fallback_value: str = '') -> str:
    text = str(encrypted_value or '').strip()
    fallback_text = str(fallback_value or '').strip()
    if fallback_text:
        raise ValueError('Password values must be encrypted before submission.')
    if not text:
        return ''
    try:
        encrypted_bytes = base64.b64decode(text.encode('utf-8'), validate=True)
        plain_bytes = _load_password_private_key().decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plain_bytes.decode('utf-8')
    except Exception as exc:
        raise ValueError('The encrypted password could not be read.') from exc


def decrypt_required_password(payload, field_name: str, fallback_field_name: str = '') -> str:
    source = payload or {}
    fallback_value = source.get(fallback_field_name) if fallback_field_name else ''
    value = decrypt_password_transport_value(source.get(field_name), fallback_value)
    if value == '':
        raise ValueError('The encrypted password is required.')
    return value


def hash_password(password: str) -> str:
    if password is None:
        raise ValueError('password is required')
    return hashlib.sha256(str(password).encode('utf-8')).hexdigest()


def verify_password(password, encoded) -> bool:
    if password is None or not encoded:
        return False
    text = str(encoded)
    candidate = str(password)
    if text.startswith(('scrypt:', 'pbkdf2:')):
        try:
            return check_password_hash(text, candidate)
        except Exception:
            return False
    if text.startswith('pbkdf2_sha256$'):
        from hashlib import pbkdf2_hmac
        import base64

        parts = text.split('$')
        if len(parts) != 4:
            return False
        _, iteration_text, salt_text, digest_text = parts
        try:
            iterations = int(iteration_text)
            salt = base64.b64decode(salt_text.encode('utf-8'))
            digest = base64.b64decode(digest_text.encode('utf-8'))
        except Exception:
            return False
        new_digest = pbkdf2_hmac('sha256', candidate.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(new_digest, digest)
    if len(text) == 64:
        return hmac.compare_digest(hashlib.sha256(candidate.encode('utf-8')).hexdigest(), text)
    return False


def validate_password_policy(password: str) -> str:
    text = str(password or '')
    if text == '':
        return 'Please enter a password.'
    return ''


def is_safe_local_image_url(value):
    text = (value or '').strip()
    if not text:
        return True
    lower = text.lower()
    return not (lower.startswith('http://') or lower.startswith('https://') or lower.startswith('//'))


def _clean_ip_token(value: str) -> str:
    text = str(value or '').strip().strip('"').strip("'")
    if not text:
        return ''
    lower = text.lower()
    if lower.startswith('for='):
        text = text.split('=', 1)[1].strip().strip('"').strip("'")
    if text.startswith('['):
        bracket_end = text.find(']')
        if bracket_end != -1:
            return text[1:bracket_end]
    if text.count(':') == 1 and '.' in text:
        host, port = text.rsplit(':', 1)
        if port.isdigit():
            text = host
    return text


def _trusted_proxy_networks():
    networks = []
    for item in parse_csv_text(current_app.config.get('TRUSTED_PROXY_CIDRS', '')):
        try:
            networks.append(ip_network(item, strict=False))
        except Exception:
            continue
    return networks


def _is_trusted_proxy(ip_text: str) -> bool:
    cleaned = _clean_ip_token(ip_text)
    if not cleaned:
        return False
    try:
        addr = ip_address(cleaned)
    except Exception:
        return False
    for network in _trusted_proxy_networks():
        if addr in network:
            return True
    return False


def _forwarded_header_ips() -> list[str]:
    values = []
    forwarded = request.headers.get('Forwarded', '')
    if forwarded:
        for part in forwarded.split(','):
            for token in part.split(';'):
                stripped = token.strip()
                if stripped.lower().startswith('for='):
                    candidate = _clean_ip_token(stripped)
                    if candidate:
                        values.append(candidate)
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        for item in xff.split(','):
            candidate = _clean_ip_token(item)
            if candidate:
                values.append(candidate)
    x_real_ip = _clean_ip_token(request.headers.get('X-Real-IP', ''))
    if x_real_ip:
        values.append(x_real_ip)
    ordered = []
    seen = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _raw_peer_ip() -> str:
    return _clean_ip_token(request.environ.get('REMOTE_ADDR') or request.remote_addr or '')


def get_client_ip():
    remote_ip = _raw_peer_ip()
    if not remote_ip:
        return 'Local Address'
    if not bool(current_app.config.get('TRUST_PROXY_HEADERS', True)):
        return remote_ip
    if not _is_trusted_proxy(remote_ip):
        return remote_ip

    forwarded_chain = _forwarded_header_ips()
    if not forwarded_chain:
        return remote_ip or 'Local Address'

    for item in reversed(forwarded_chain):
        if not _is_trusted_proxy(item):
            return item
    return forwarded_chain[0]

def extract_request_identity():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return {
            'id': payload.get('id'),
            'username': payload.get('username') or '',
            'iat': payload.get('iat'),
            'exp': payload.get('exp'),
        }
    except Exception:
        return None


