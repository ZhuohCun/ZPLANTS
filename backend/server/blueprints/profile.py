from flask import Blueprint, g, request

from server.auth import auth_required, build_user_query, inflate_user
from server.common import FEATURE_TO_MODULE_ID
from server.db import get_db
from server.logger import append_log
from server.responses import fail, now_string, success
from server.security import decrypt_required_password, hash_password, validate_password_policy, verify_password

profile_bp = Blueprint('profile', __name__)


def _normalize_phone(value):
    table = str.maketrans('０１２３４５６７８９', '0123456789')
    return ''.join(ch for ch in str(value or '').translate(table) if ch.isdigit())


def _validate_profile_fields(phone, email):
    phone = _normalize_phone(phone)
    email = str(email or '').strip()
    if not phone:
        return 'Enter a phone number.'
    if not email:
        return 'Enter an email address.'
    if not phone.isdigit() or len(phone) != 11:
        return 'Enter an 11-digit phone number.'
    if '@' not in email:
        return 'Enter a valid email address.'
    return ''


@profile_bp.get('/profile/detail')
@auth_required()
def profile():
    return success(g.current_user, 'Loaded')


@profile_bp.put('/profile/update')
@auth_required()
def update_profile():
    payload = request.get_json(silent=True) or {}
    real_name = (payload.get('realName') or g.current_user.get('realName') or '').strip()
    phone = _normalize_phone(payload.get('phone', g.current_user.get('phone', '')))
    email = str(payload.get('email', g.current_user.get('email', ''))).strip()
    profile_error = _validate_profile_fields(phone, email)
    if profile_error:
        return fail(1011, profile_error)
    db = get_db()
    db.execute('update users set real_name = ?, phone = ?, email = ?, update_time = ? where id = ?', (real_name, phone, email, now_string(), g.current_user['id']))
    db.commit()
    row = db.fetchone(build_user_query('where u.id = ?'), (g.current_user['id'],))
    append_log(g.current_user, 'Edit Details', '/api/auth/profile', 'PUT', FEATURE_TO_MODULE_ID['profile'])
    return success(inflate_user(row), 'Updated')


@profile_bp.put('/password')
@auth_required()
def update_password():
    payload = request.get_json(silent=True) or {}
    try:
        old_password = decrypt_required_password(payload, 'encryptedOldPassword')
        new_password = decrypt_required_password(payload, 'encryptedNewPassword')
        confirm_password = decrypt_required_password(payload, 'encryptedConfirmPassword')
    except ValueError as exc:
        return fail(1013, str(exc))
    if new_password != confirm_password:
        return fail(1012, 'The two passwords do not match.')
    policy_error = validate_password_policy(new_password)
    if policy_error:
        return fail(1013, policy_error)
    db = get_db()
    row = db.fetchone('select password from users where id = ?', (g.current_user['id'],))
    if not row or not verify_password(old_password, row.get('password')):
        return fail(1014, 'The current password is incorrect.')
    db.execute('update users set password = ?, update_time = ? where id = ?', (hash_password(new_password), now_string(), g.current_user['id']))
    db.commit()
    append_log(g.current_user, 'Change Password', '/api/auth/password', 'PUT', FEATURE_TO_MODULE_ID['profile'])
    return success({}, 'Updated')
