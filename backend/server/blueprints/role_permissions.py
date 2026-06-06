from flask import Blueprint, g, request
from server.auth import auth_required
from server.common import PERMISSION_GROUP_TEXT, ensure_system_catalog, role_key_from_name, role_name_from_key, feature_code_from_module_row, permission_key_from_row, FEATURE_TO_ROUTE, FEATURE_TO_MODULE_ID
from server.db import get_db
from server.logger import append_log
from server.responses import fail, now_string, success
from server.cache import invalidate_namespaces, redis_remember_json

role_permissions_bp = Blueprint('role_permissions', __name__)

def _is_enabled(state):
    return int(state or 0) in [2, 3]

def _is_recognition_history_permission(feature_key, permission_key):
    return feature_key == 'recognition' and permission_key == 'view_records'


def _perm_group(item):
    value = item.get('permissionGroup')
    if value is None:
        value = item.get('permission_group')
    return int(value if value is not None else -1)

def _is_locked_state(state):
    return int(state or 0) in [0, 3]

def _validate_module_rules(permission_rows):
    basic_enabled = any(_perm_group(item) == 0 and _is_enabled(item.get('state')) for item in permission_rows)
    other_enabled = any(_perm_group(item) in [1, 2] and _is_enabled(item.get('state')) for item in permission_rows)
    if other_enabled and not basic_enabled:
        return False, 'Turn on the basic permission for this feature first.'
    return True, ''

def _validate_basic_close(permission_rows):
    basic_item = next((item for item in permission_rows if _perm_group(item) == 0), None)
    if basic_item and int(basic_item.get('state') or 0) in [0, 1]:
        other_enabled = any(_perm_group(item) in [1, 2] and _is_enabled(item.get('state')) for item in permission_rows)
        if other_enabled:
            return False, 'Turn off the other permissions under this feature for the role first.'
    return True, ''

def _load_permission_rows(db, role_id, module_id):
    rows = db.fetchall(
        '''select p.id as permission_id, p.permission_name, p.permission_group, p.sort_no, rp.id as relation_id, rp.state, m.route_path, m.sort_no as module_sort_no
           from permissions p
           left join modules m on p.module_id = m.id
           left join role_permissions rp on rp.permission_id = p.id and rp.role_id = ?
           where p.module_id = ?
           order by p.sort_no asc, p.id asc''',
        (role_id, module_id),
    )
    result = []
    for row in rows:
        item = dict(row)
        feature_key = feature_code_from_module_row(item)
        item['permission_key'] = permission_key_from_row(feature_key, item)
        result.append(item)
    return result

@role_permissions_bp.get('/features/list')
@auth_required()
def list_access_matrix():
    def producer():
        db = get_db()
        ensure_system_catalog(db)
        roles = db.fetchall('select * from roles order by id asc')
        modules = db.fetchall('select * from modules order by sort_no asc, id asc')
        matrix = []
        for role in roles:
            role_key = role_key_from_name(role['role_name'])
            for module in modules:
                feature_key = feature_code_from_module_row(module)
                perm_rows = _load_permission_rows(db, role['id'], module['id'])
                item = {'roleCode': role_key, 'roleName': role['role_name'], 'moduleCode': feature_key, 'moduleName': module['module_name'], 'permissions': []}
                for perm in perm_rows:
                    state = int(perm.get('state') or 0)
                    item['permissions'].append({'permissionCode': perm['permission_key'], 'permissionName': perm['permission_name'], 'permissionGroup': int(perm.get('permission_group') or 0), 'permissionGroupText': PERMISSION_GROUP_TEXT.get(int(perm.get('permission_group') or 0), ''), 'state': state, 'locked': _is_locked_state(state)})
                matrix.append(item)
        return {'matrix': matrix}

    return success(redis_remember_json('access_matrix', ('all',), 120, producer), 'Loaded')

@role_permissions_bp.put('/features/update')
@auth_required()
def update_access_matrix():
    payload = request.get_json(silent=True) or {}
    role_code = payload.get('roleCode')
    modules = payload.get('modules') or payload.get('features') or []
    if not isinstance(modules, list) or not modules:
        return fail(1704, 'No changes were submitted.')
    db = get_db()
    ensure_system_catalog(db)
    role = db.fetchone('select * from roles where role_name = ?', (role_name_from_key(role_code),))
    if not role:
        return fail(1702, 'The role was not found.')
    role_key = role_key_from_name(role['role_name'])
    updates, inserts = [], []
    now = now_string()
    for module_item in modules:
        feature_key = module_item.get('moduleCode')
        incoming_permissions = module_item.get('permissions') or []
        module = db.fetchone('select * from modules where route_path = ?', (FEATURE_TO_ROUTE.get(feature_key, ''),))
        if not module:
            return fail(1702, 'The feature was not found.')
        rows = _load_permission_rows(db, role['id'], module['id'])
        incoming_map = {item.get('permissionCode'): int(item.get('state') or 0) for item in incoming_permissions}
        merged = []
        for row in rows:
            current_state = int(row.get('state') or 0)
            next_state = incoming_map.get(row['permission_key'], current_state)
            if next_state not in [0, 1, 2, 3]:
                return fail(1704, 'The permission state is not valid.')
            if current_state in [0, 3] and next_state != current_state:
                return fail(1709, 'Always-on or always-off permissions cannot be changed from this page', 403)
            merged.append({'permissionCode': row['permission_key'], 'permissionGroup': int(row.get('permission_group') or 0), 'state': next_state, 'relationId': row.get('relation_id'), 'permissionId': row['permission_id'], 'currentState': current_state})
        ok, message = _validate_basic_close(merged)
        if not ok:
            return fail(1709, message, 403)
        ok, message = _validate_module_rules(merged)
        if not ok:
            return fail(1709, message, 403)
        for item in merged:
            if int(item['state']) == int(item['currentState']):
                continue
            if item['relationId']:
                updates.append((int(item['state']), now, role['id'], item['permissionId']))
            else:
                inserts.append((role['id'], item['permissionId'], int(item['state']), now))
    for state, update_time, role_id, permission_id in updates:
        db.execute('update role_permissions set state = ?, update_time = ? where role_id = ? and permission_id = ?', (state, update_time, role_id, permission_id))
    for role_id, permission_id, state, update_time in inserts:
        db.execute('insert into role_permissions (role_id, permission_id, state, update_time) values (?, ?, ?, ?)', (role_id, permission_id, state, update_time))
    db.commit()
    invalidate_namespaces('access_matrix')
    append_log(g.current_user, 'Update Role Permissions', '/api/access/features', 'PUT', FEATURE_TO_MODULE_ID['access'])
    return success({}, 'Saved')

