from flask import Blueprint, request, g
from server.auth import auth_required
from server.db import get_db
from server.responses import success, fail, now_string
from server.logger import append_log
from server.utils import paginate, format_display_datetime
from server.security import decrypt_password_transport_value, decrypt_required_password, hash_password, validate_password_policy
from server.common import choose_primary_role, list_roles_for_user, role_key_from_name, role_name_from_key, FEATURE_TO_MODULE_ID

user_management_bp = Blueprint('user_management', __name__)

def _normalize_phone(value):
    table = str.maketrans('０１２３４５６７８９', '0123456789')
    return ''.join(ch for ch in str(value or '').translate(table) if ch.isdigit())


def _validate_profile_fields(phone, email):
    phone = str(phone or '').strip()
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

def _enabled_admin_count(exclude_user_id=None):
    db = get_db()
    sql = '''select count(distinct u.id) as count from users u left join roles r on u.role_id = r.id where u.is_disabled = 0 and r.role_name = ? '''
    params = [role_name_from_key('admin')]
    if exclude_user_id is not None:
        sql += ' and u.id <> ?'
        params.append(exclude_user_id)
    row = db.fetchone(sql, tuple(params))
    return int(row.get('count') or 0)

def _user_role_codes(user_id):
    return [role_key_from_name(item['role_name']) for item in list_roles_for_user(user_id)]

def serialize_user(row):
    roles = list_roles_for_user(row['id'])
    role_codes = [role_key_from_name(item['role_name']) for item in roles]
    role_names = [item['role_name'] for item in roles]
    status_code = 0 if int(row.get('is_disabled') or 0) else 1
    return {'id': row['id'],'username': row.get('username', ''),'realName': row.get('real_name', ''),'phone': row.get('phone', ''),'email': row.get('email', ''),'role': choose_primary_role(role_codes),'roleName': ', '.join(role_names),'status': 'Enabled' if status_code == 1 else 'Disabled','statusCode': status_code,'createTime': format_display_datetime(row.get('create_time', '')),'disableReason': row.get('disable_reason', ''),'disabledByName': row.get('disabled_by_name', ''),'disabledTime': format_display_datetime(row.get('disabled_time', ''))}

@user_management_bp.get('/list')
@auth_required()
def list_users():
    keyword = (request.args.get('keyword') or '').strip()
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)
    db = get_db()
    rows = db.fetchall('select u.*, du.real_name as disabled_by_name from users u left join users du on u.disabled_by_user_id = du.id order by u.id asc')
    data = []
    for row in rows:
        item = serialize_user(row)
        text = f"{item.get('username','')}{item.get('realName','')}{item.get('email','')}{item.get('roleName','')}{item.get('disableReason','')}"
        if keyword and keyword not in text:
            continue
        data.append(item)
    return success(paginate(data, page_num, page_size), 'Loaded')

@user_management_bp.post('/create')
@auth_required()
def create_user():
    payload = request.get_json(silent=True) or {}
    payload['phone'] = str(payload.get('phone', '')).strip()
    username = (payload.get('username') or '').strip()
    real_name = (payload.get('realName') or '').strip()
    phone = _normalize_phone(payload.get('phone', ''))
    email = str(payload.get('email', '')).strip()
    if not username or not real_name:
        return fail(1501, 'Enter both username and full name.')
    profile_error = _validate_profile_fields(phone, email)
    if profile_error:
        return fail(1508, profile_error)
    db = get_db()
    exists = db.fetchone('select id from users where username = ?', (username,))
    if exists:
        return fail(1502, 'This username is already in use.')
    now = now_string()
    try:
        raw_password = decrypt_required_password(payload, 'encryptedPassword')
    except ValueError as exc:
        return fail(1509, str(exc))
    password_error = validate_password_policy(raw_password)
    if password_error:
        return fail(1509, password_error)
    role_key = payload.get('role', 'user')
    role = db.fetchone('select * from roles where role_name = ?', (role_name_from_key(role_key),))
    role_id = role['id'] if role else 3
    status_code = int(payload.get('statusCode') or 1)
    disable_reason = (payload.get('disableReason') or '').strip() if status_code == 0 else ''
    disabled_by_user_id = g.current_user['id'] if status_code == 0 else None
    disabled_time = now if status_code == 0 else None
    if status_code == 1:
        disabled_time = None
    if status_code == 1:
        insert_params_core = (username, hash_password(raw_password), real_name, phone, email, role_id, 0, '', None, None)
        insert_params = insert_params_core + (now, now)
    else:
        insert_params_core = (username, hash_password(raw_password), real_name, phone, email, role_id, 1, disable_reason, disabled_by_user_id, disabled_time)
        insert_params = insert_params_core + (now, now)
    cursor = db.execute('insert into users (username, password, real_name, phone, email, role_id, is_disabled, disable_reason, disabled_by_user_id, disabled_time, create_time, update_time) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', insert_params)
    user_id = cursor.lastrowid
    db.commit()
    append_log(g.current_user, 'Add User', '/api/users', 'POST', FEATURE_TO_MODULE_ID['users'])
    return success(serialize_user(db.fetchone('select u.*, du.real_name as disabled_by_name from users u left join users du on u.disabled_by_user_id = du.id where u.id = ?', (user_id,))), 'Added')

@user_management_bp.put('/update/<int:user_id>')
@auth_required()
def update_user(user_id):
    payload = request.get_json(silent=True) or {}
    payload['phone'] = _normalize_phone(payload.get('phone', ''))
    payload['email'] = str(payload.get('email', '')).strip()
    db = get_db()
    row = db.fetchone('select * from users where id = ?', (user_id,))
    if not row:
        return fail(1503, 'The user was not found.')
    if not payload['phone']:
        payload['phone'] = str(row.get('phone', '')).strip()
    if not payload['email']:
        payload['email'] = str(row.get('email', '')).strip()
    profile_error = _validate_profile_fields(payload.get('phone', ''), payload.get('email', ''))
    if profile_error:
        return fail(1508, profile_error)
    current_roles = _user_role_codes(user_id)
    target_role = payload.get('role')
    current_is_admin = 'admin' in current_roles
    target_is_admin = target_role == 'admin' if target_role else current_is_admin
    target_status = int(payload.get('statusCode') if payload.get('statusCode') is not None else (0 if int(row.get('is_disabled') or 0) else 1))
    disable_reason = (payload.get('disableReason') if payload.get('disableReason') is not None else row.get('disable_reason', '')) or ''
    if current_is_admin and (not target_is_admin or target_status != 1) and _enabled_admin_count(exclude_user_id=user_id) <= 0:
        return fail(1506, 'At least one enabled administrator account must remain.', 403)
    if target_status == 0 and not disable_reason:
        return fail(1507, 'Enter a reason for disabling the account.')
    new_password = row['password']
    try:
        decrypted_password = decrypt_password_transport_value(payload.get('encryptedPassword'))
    except ValueError as exc:
        return fail(1509, str(exc))
    if decrypted_password:
        password_error = validate_password_policy(decrypted_password)
        if password_error:
            return fail(1509, password_error)
        new_password = hash_password(decrypted_password)
    role_id = row.get('role_id')
    if target_role:
        role = db.fetchone('select * from roles where role_name = ?', (role_name_from_key(target_role),))
        if role:
            role_id = role['id']
    db.execute('update users set username = ?, password = ?, real_name = ?, phone = ?, email = ?, role_id = ?, is_disabled = ?, update_time = ?, disable_reason = ?, disabled_by_user_id = ?, disabled_time = ? where id = ?', ((payload.get('username') or row.get('username', '')).strip(), new_password, (payload.get('realName') or row.get('real_name', '')).strip(), payload.get('phone', row.get('phone', '')), payload.get('email', row.get('email', '')), role_id, 0 if target_status == 1 else 1, now_string(), '' if target_status == 1 else disable_reason, None if target_status == 1 else g.current_user['id'], None if target_status == 1 else now_string(), user_id))
    db.commit()
    append_log(g.current_user, 'Edit User', f'/api/users/{user_id}', 'PUT', FEATURE_TO_MODULE_ID['users'])
    return success(serialize_user(db.fetchone('select u.*, du.real_name as disabled_by_name from users u left join users du on u.disabled_by_user_id = du.id where u.id = ?', (user_id,))), 'Updated')
