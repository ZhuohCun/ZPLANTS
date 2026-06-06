import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import current_app, g, request
from server.common import base_permission_keys, choose_primary_role, ensure_system_catalog, get_edit_module_codes_for_role_ids, get_enabled_module_codes_for_role_ids, get_permission_map_for_role_ids, list_roles_for_user, role_key_from_name
from server.db import get_db
from server.responses import fail

def build_user_query(where_clause=''):
    sql = 'select u.* from users u where 1 = 1'
    if where_clause:
        clause = where_clause.strip()
        sql += (' and ' + clause[6:]) if clause.lower().startswith('where ') else (' ' + clause)
    return sql

def generate_token(user):
    now = datetime.now(timezone.utc)
    return jwt.encode({'id': user['id'], 'username': user['username'], 'iat': now, 'exp': now + timedelta(seconds=int(current_app.config['TOKEN_EXPIRE_SECONDS']))}, current_app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])

def inflate_user(user_row):
    roles = [{'id': item['id'], 'role_name': item.get('role_name', ''), 'role_key': role_key_from_name(item.get('role_name', ''))} for item in list_roles_for_user(user_row['id'])]
    role_ids = [r['id'] for r in roles]
    role_codes = [r.get('role_key') or r.get('role_name') for r in roles]
    primary = choose_primary_role(role_codes)
    user = dict(user_row)
    user['realName'] = user.get('real_name', '') or ''
    user['roleName'] = ', '.join([r.get('role_name', '') for r in roles if r.get('role_name')])
    user['roles'] = role_codes; user['roleIds'] = role_ids; user['role'] = primary
    db = get_db(); ensure_system_catalog(db)
    user['features'] = get_enabled_module_codes_for_role_ids(role_ids)
    user['editableFeatures'] = get_edit_module_codes_for_role_ids(role_ids)
    raw_map = get_permission_map_for_role_ids(role_ids); permission_map = {}
    for feature, state_map in raw_map.items():
        permission_map[feature] = [code for code, state in state_map.items() if int(state or 0) in [2, 3]]
    user['features'] = list(dict.fromkeys(user['features'] + [feature for feature, perms in permission_map.items() if any(code in perms for code in base_permission_keys(feature))]))
    user['permissionMap'] = permission_map
    return user

def get_request_user():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '): return None
    token = auth_header.split(' ', 1)[1].strip()
    if not token: return None
    try: payload = decode_token(token)
    except Exception: return None
    db = get_db(); ensure_system_catalog(db)
    row = db.fetchone(build_user_query('where u.id = ?'), (payload['id'],))
    if not row or int(row.get('is_disabled') or 0) == 1: return None
    return inflate_user(row)

def resolve_required_feature(path, method):
    mappings = [('/api/dashboard', 'home'),('/api/recognitions', 'recognition'),('/api/species', 'species'),('/api/plants', 'plant'),('/api/locations', 'zone_location'),('/api/care/methods', 'care_method'),('/api/care', 'care'),('/api/feedbacks', 'feedback'),('/api/users', 'users'),('/api/logs', 'logs'),('/api/access', 'access'),('/api/auth/profile', 'profile'),('/api/auth/password', 'profile'),('/api/auth/logout', 'profile')]
    for prefix, feature in mappings:
        if path.startswith(prefix): return feature
    return ''

def resolve_required_permission(path, method):
    if path.startswith('/api/dashboard'): return 'view'
    if path.startswith('/api/recognitions/options'): return 'view_records'
    if path == '/api/recognitions': return 'view_records' if method == 'GET' else 'capture'
    if path.startswith('/api/recognitions/') and method == 'GET' and path.rsplit('/', 1)[-1].isdigit(): return 'capture'
    if path.startswith('/api/recognitions/'): return 'view_records' if method == 'GET' else 'capture'
    if path.startswith('/api/species'): return {'GET':'view','POST':'create','PUT':'update','DELETE':'delete'}.get(method, 'view')
    if path.startswith('/api/plants'): return {'GET':'view','POST':'create','PUT':'update','DELETE':'delete'}.get(method, 'view')
    if path.startswith('/api/locations'): return {'GET':'view','POST':'create','PUT':'update','DELETE':'delete'}.get(method, 'view')
    if path.startswith('/api/care/reminders/') and path.endswith('/process'): return 'ignore' if (request.get_json(silent=True) or {}).get('processResult') == 3 else 'process'
    if path.startswith('/api/care/methods'): return {'GET':'view','POST':'create','PUT':'update','DELETE':'delete'}.get(method, 'view')
    if path.startswith('/api/care/rules'): return 'view' if method == 'GET' else 'update'
    if path.startswith('/api/care'): return 'view' if method == 'GET' else 'process'
    if path.startswith('/api/feedbacks'): return 'audit' if '/audit' in path else ('submit' if method == 'POST' else 'view')
    if path.startswith('/api/users'): return 'view' if method == 'GET' else 'update'
    if path.startswith('/api/logs'): return 'view'
    if path.startswith('/api/access/features'): return 'configure' if method in ['PUT', 'POST'] else 'view'
    if path.startswith('/api/auth/profile'): return 'update_profile' if method == 'PUT' else 'view'
    if path.startswith('/api/auth/password'): return 'update_profile'
    return 'view'

def has_feature_permission(user, feature, permission):
    if not feature:
        return True
    permission_list = user.get('permissionMap', {}).get(feature, [])
    base_keys = base_permission_keys(feature)
    if base_keys and not any(code in permission_list for code in base_keys):
        return False
    return (not permission) or permission in permission_list

def auth_required(roles=None):
    roles = roles or []
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_request_user()
            if not user: return fail(401, 'Please sign in again.', 401)
            if roles and user.get('role') not in roles: return fail(403, 'You do not have access to this feature.', 403)
            feature = resolve_required_feature(request.path or '', request.method or 'GET')
            permission = resolve_required_permission(request.path or '', request.method or 'GET')
            if not has_feature_permission(user, feature, permission): return fail(403, 'This account does not have the required permission.', 403)
            g.current_user = user
            return func(*args, **kwargs)
        return wrapper
    return deco
