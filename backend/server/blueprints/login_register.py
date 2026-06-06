from flask import Blueprint, request, g, current_app
from server.db import get_db
from server.responses import success, fail, now_string
from server.auth import generate_token, auth_required, build_user_query, inflate_user
from server.security import decrypt_required_password, hash_password, validate_password_policy, verify_password
from server.logger import append_log
from server.common import FEATURE_TO_MODULE_ID

login_register_bp = Blueprint('login_register', __name__)

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

def _login_log_user(user_row):
    return {
        'id': user_row.get('id'),
        'username': user_row.get('username', ''),
        'real_name': user_row.get('real_name', ''),
        'realName': user_row.get('real_name', '') or '',
    }


@login_register_bp.post('/login')
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    try:
        password = decrypt_required_password(payload, 'encryptedPassword')
    except ValueError as exc:
        return fail(1000, str(exc))
    if not username:
        return fail(1000, 'Enter a username.')
    db = get_db()
    user_row = db.fetchone(build_user_query('where u.username = ?'), (username,))
    if not user_row:
        append_log(None, 'Sign-in failed', '/api/auth/login', 'POST', FEATURE_TO_MODULE_ID['home'], extra_remark='The username was not found.')
        return fail(1001, 'The username or password is incorrect.')
    login_log_user = _login_log_user(user_row)
    if not verify_password(password, user_row.get('password')):
        append_log(login_log_user, 'Sign-in failed', '/api/auth/login', 'POST', FEATURE_TO_MODULE_ID['home'], extra_remark='The password is incorrect.')
        return fail(1002, 'The username or password is incorrect.')
    if int(user_row.get('is_disabled') or 0) == 1:
        append_log(login_log_user, 'Sign-in failed', '/api/auth/login', 'POST', FEATURE_TO_MODULE_ID['home'], extra_remark='This account has been disabled.')
        return fail(1003, 'This account has been disabled.')
    user = inflate_user(user_row)
    token = generate_token(user)
    append_log(user, 'User Sign-in', '/api/auth/login', 'POST', FEATURE_TO_MODULE_ID['home'])
    return success({'token': token, 'userInfo': user}, 'Signed in')


@login_register_bp.post('/register')
def register():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    real_name = (payload.get('realName') or '').strip()
    phone = _normalize_phone(payload.get('phone'))
    email = (payload.get('email') or '').strip()
    try:
        password = decrypt_required_password(payload, 'encryptedPassword')
        confirm_password = decrypt_required_password(payload, 'encryptedConfirmPassword')
    except ValueError as exc:
        return fail(1004, str(exc))
    if not username or not real_name or not phone or not email:
        return fail(1004, 'Fill in the registration information.')
    if password != confirm_password:
        return fail(1005, 'The two passwords do not match.')
    password_error = validate_password_policy(password)
    if password_error:
        return fail(1013, password_error)
    profile_error = _validate_profile_fields(phone, email)
    if profile_error:
        return fail(1011, profile_error)
    db = get_db()
    exists = db.fetchone('select id from users where username = ?', (username,))
    if exists:
        return fail(1006, 'This username is already in use.')
    now = now_string()
    user_id = db.execute('insert into users (username, password, real_name, phone, email, role_id, is_disabled, disable_reason, disabled_by_user_id, disabled_time, create_time, update_time) values (?, ?, ?, ?, ?, 3, 0, ?, ?, ?, ?, ?)', (username, hash_password(password), real_name, phone, email, '', None, None, now, now)).lastrowid
    db.commit()
    append_log({'id': user_id}, 'User Registration', '/api/auth/register', 'POST', FEATURE_TO_MODULE_ID['home'])
    return success({'userId': user_id}, 'Registration complete')


@login_register_bp.post('/logout')
@auth_required()
def logout():
    append_log(g.current_user, 'Sign Out', '/api/auth/logout', 'POST', FEATURE_TO_MODULE_ID['profile'])
    return success({}, 'Signed out')
