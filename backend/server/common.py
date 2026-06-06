from threading import Lock

from server.db import get_db

RFP_STATE_TEXT = {0: 'Off', 1: 'Off', 2: 'On', 3: 'On'}
REMINDER_STATUS_TEXT = {1: 'Pending', 2: 'Completed', 3: 'Dismissed'}
FEEDBACK_STATUS_TEXT = {1: 'Awaiting Review', 2: 'Approved', 3: 'Rejected'}
FEEDBACK_TYPE_TEXT = {1: 'Experience Feedback', 2: 'Recognition Feedback', 3: 'Other'}
ROLE_PRIORITY = ['admin', 'manager', 'user']
ROLE_NAME_MAP = {'admin': 'System Administrator', 'manager': 'Grounds Maintenance', 'user': 'General User'}
ROLE_NAME_REVERSE_MAP = {value: key for key, value in ROLE_NAME_MAP.items()}
IMMUTABLE_FEATURE_CODES = {'home', 'recognition', 'species', 'profile'}
ADMIN_ONLY_FEATURE_CODES = {'access', 'hash_tool'}
PERMISSION_GROUP_TEXT = {0: 'Basic Permissions', 1: 'Standard Permissions', 2: 'Extended Permissions'}
DEFAULT_MODULES = [
    ('home', 'Home', '/home', 1),
    ('recognition', 'Plant Recognition', '/recognition/upload', 2),
    ('species', 'Plant Species', '/species', 3),
    ('plant', 'Plant Management', '/plants', 4),
    ('care', 'Care Reminders', '/care', 5),
    ('care_method', 'Care Method Management', '/care/methods-manage', 6),
    ('feedback', 'Feedback Center', '/feedback', 7),
    ('users', 'User Management', '/admin/users', 8),
    ('logs', 'Operation Logs', '/admin/logs', 9),
    ('zone_location', 'Zone and Location Management', '/admin/locations', 10),
    ('profile', 'Profile', '/profile', 11),
    ('access', 'Role Permissions', '/admin/access', 12),
    ('hash_tool', 'Password Hash', '/admin/hash', 13),
]
DEFAULT_PERMISSIONS = {
    'home': [('view', 'Open Home', 0, 1)],
    'recognition': [('capture', 'Plant Recognition', 0, 1), ('view_records', 'View Recognition Records', 1, 2)],
    'species': [('view', 'View Plant Species', 0, 1), ('view_distribution', 'View Plant Distribution', 1, 2), ('create', 'Add Plant Species', 2, 3), ('update', 'Edit Plant Species', 2, 4), ('delete', 'Delete Plant Species', 2, 5)],
    'plant': [('view', 'View Plant Management', 0, 1), ('create', 'Add Plant', 2, 2), ('update', 'Edit Plant', 2, 3), ('delete', 'Delete Plant', 2, 4)],
    'care': [('view', 'View Care Reminders', 0, 1), ('process', 'Complete Care Reminder', 1, 2), ('ignore', 'Dismiss Care Reminder', 1, 3)],
    'care_method': [('view', 'View Care Methods', 0, 1), ('create', 'Add Care Method', 2, 2), ('update', 'Edit Care Method', 2, 3), ('delete', 'Delete Care Method', 2, 4)],
    'feedback': [('view', 'View Feedback', 0, 1), ('submit', 'Send Feedback', 1, 2), ('audit', 'Review Feedback', 2, 3)],
    'users': [('view', 'View Users', 0, 1), ('update', 'Edit User', 2, 2), ('disable', 'Disable User', 2, 3)],
    'logs': [('view', 'View Logs', 0, 1)],
    'zone_location': [('view', 'View Zones and Locations', 0, 1), ('create', 'Add Zone or Location', 2, 2), ('update', 'Edit Zone or Location', 2, 3), ('delete', 'Delete Zone or Location', 2, 4)],
    'profile': [('view', 'Open Profile', 0, 1), ('update_profile', 'Edit Details', 1, 2)],
    'access': [('view', 'View Permission Matrix', 0, 1), ('configure', 'Configure Permission Matrix', 2, 2)],
    'hash_tool': [('calculate', 'Generate Password Hash', 0, 1)],
}
FEATURE_TO_MODULE_ID = {feature: index for index, (feature, *_rest) in enumerate(DEFAULT_MODULES, start=1)}
FEATURE_TO_ROUTE = {feature: route_path for feature, _name, route_path, _sort in DEFAULT_MODULES}
ROUTE_TO_FEATURE = {route_path: feature for feature, _name, route_path, _sort in DEFAULT_MODULES}
PERMISSION_SORT_TO_KEY = {feature: {sort_no: permission_key for permission_key, _permission_name, _group, sort_no in definitions} for feature, definitions in DEFAULT_PERMISSIONS.items()}
PERMISSION_KEY_TO_NAME = {feature: {permission_key: permission_name for permission_key, permission_name, _group, _sort in definitions} for feature, definitions in DEFAULT_PERMISSIONS.items()}
_catalog_lock = Lock()
_catalog_ready = False

def role_key_from_name(role_name):
    return ROLE_NAME_REVERSE_MAP.get(str(role_name or '').strip(), '')

def role_name_from_key(role_key):
    return ROLE_NAME_MAP.get(str(role_key or '').strip(), '')

def choose_primary_role(role_codes):
    for item in ROLE_PRIORITY:
        if item in role_codes:
            return item
    return role_codes[0] if role_codes else ''

def feature_code_from_module_row(module_row):
    if not module_row:
        return ''
    route_path = str(module_row.get('route_path') or '').strip()
    feature = ROUTE_TO_FEATURE.get(route_path)
    if feature:
        return feature
    sort_no = int(module_row.get('sort_no') or module_row.get('module_sort_no') or 0)
    for code, _name, _route, sort in DEFAULT_MODULES:
        if sort == sort_no:
            return code
    return ''

feature_key_from_module_row = feature_code_from_module_row

def permission_key_from_row(feature_code, permission_row):
    if not feature_code or not permission_row:
        return ''
    sort_no = int(permission_row.get('sort_no') or permission_row.get('permission_sort_no') or 0)
    code = PERMISSION_SORT_TO_KEY.get(feature_code, {}).get(sort_no)
    if code:
        return code
    permission_name = str(permission_row.get('permission_name') or '').strip()
    for item_code, item_name in PERMISSION_KEY_TO_NAME.get(feature_code, {}).items():
        if item_name == permission_name:
            return item_code
    return ''

def base_permission_keys(feature):
    return [code for code, _name, group, *_rest in DEFAULT_PERMISSIONS.get(feature, []) if int(group) == 0]

def _permission_rows(role_ids):
    if not role_ids:
        return []
    db = get_db()
    ensure_system_catalog(db)
    placeholders = ','.join(['?'] * len(role_ids))
    raw_rows = db.fetchall(
        f'''select m.id as module_id, m.module_name, m.route_path, m.sort_no as module_sort_no,
                   p.id as permission_id, p.permission_name, p.permission_group, p.sort_no as permission_sort_no,
                   max(rp.state) as state
            from role_permissions rp
            left join permissions p on rp.permission_id = p.id
            left join modules m on p.module_id = m.id
            where rp.role_id in ({placeholders}) and p.id is not null and m.id is not null
            group by m.id, m.module_name, m.route_path, m.sort_no, p.id, p.permission_name, p.permission_group, p.sort_no''',
        tuple(role_ids),
    )
    rows = []
    for raw in raw_rows:
        feature = feature_code_from_module_row(raw)
        permission_key = permission_key_from_row(feature, raw)
        if feature and permission_key:
            row = dict(raw)
            row['moduleCode'] = feature
            row['permissionCode'] = permission_key
            rows.append(row)
    return rows

def get_permission_map_for_role_ids(role_ids):
    permission_map = {}
    for row in _permission_rows(role_ids):
        permission_map.setdefault(row['moduleCode'], {})[row['permissionCode']] = int(row.get('state') or 0)
    return permission_map

def get_enabled_feature_keys_for_role_ids(role_ids):
    enabled = []
    for row in _permission_rows(role_ids):
        if int(row.get('permission_group') or -1) == 0 and int(row.get('state') or 0) in [2, 3] and row['moduleCode'] not in enabled:
            enabled.append(row['moduleCode'])
    return enabled

get_enabled_module_codes_for_role_ids = get_enabled_feature_keys_for_role_ids

def get_edit_feature_keys_for_role_ids(role_ids):
    enabled = []
    for row in _permission_rows(role_ids):
        if int(row.get('permission_group') or -1) == 2 and int(row.get('state') or 0) in [2, 3] and row['moduleCode'] not in enabled:
            enabled.append(row['moduleCode'])
    return enabled

get_edit_module_codes_for_role_ids = get_edit_feature_keys_for_role_ids

def list_roles_for_user(user_id):
    return get_db().fetchall('select r.id, r.role_name from users u left join roles r on u.role_id = r.id where u.id = ? order by r.id asc', (user_id,))

def resolve_feedback_type_id(v):
    if str(v).isdigit():
        return int(v)
    rev = {vv: kk for kk, vv in FEEDBACK_TYPE_TEXT.items()}
    return rev.get(v, 1)

def get_species_location_items(species_id):
    rows = get_db().fetchall('''select z.zone_name, l.location_name, z.id as zone_id, l.id as location_id from plants p left join locations l on p.location_id = l.id and l.is_deleted = 0 left join campus_zones z on l.zone_id = z.id and z.is_deleted = 0 where p.species_id = ? and p.is_deleted = 0 order by z.zone_name asc, l.location_name asc''', (species_id,))
    seen = set(); result = []
    for row in rows:
        key = (row.get('zone_id'), row.get('location_id'))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result

def get_species_distribution_text(species_id):
    parts = []
    for row in get_species_location_items(species_id):
        zone_name = row.get('zone_name') or ''
        location_name = row.get('location_name') or ''
        text = f'{zone_name} - {location_name}' if zone_name else location_name
        if text and text not in parts:
            parts.append(text)
    return ', '.join(parts)

def _compute_default_state(role_key, feature_key, permission_key):
    if role_key == 'admin': return 3
    if feature_key == 'recognition' and permission_key == 'view_records': return 3
    if feature_key in ADMIN_ONLY_FEATURE_CODES: return 0
    manager_enabled = {('recognition','capture'),('recognition','view_records'),('feedback','submit'),('feedback','view'),('species','view_distribution'),('plant','view'),('plant','create'),('plant','update'),('plant','delete'),('care','view'),('care','process'),('care','ignore'),('care_method','view'),('care_method','create'),('care_method','update'),('care_method','delete'),('zone_location','view'),('zone_location','create'),('zone_location','update'),('zone_location','delete'),('profile','update_profile')}
    user_enabled = {('recognition','capture'),('recognition','view_records'),('feedback','view'),('feedback','submit'),('profile','update_profile'),('species','view_distribution')}
    definitions = DEFAULT_PERMISSIONS.get(feature_key, [])
    perm_group = next((int(group) for code, _n, group, *_ in definitions if code == permission_key), None)
    if feature_key in IMMUTABLE_FEATURE_CODES and perm_group == 0: return 3
    enabled = manager_enabled if role_key == 'manager' else user_enabled
    return 2 if (feature_key, permission_key) in enabled else 1

def ensure_system_catalog(db=None):
    global _catalog_ready
    if _catalog_ready:
        return
    with _catalog_lock:
        if _catalog_ready:
            return
        db = db or get_db()
        roles = db.fetchall('select id, role_name from roles order by id asc')
        module_ids = {}
        for feature_key, module_name, route_path, sort_no in DEFAULT_MODULES:
            row = db.fetchone('select id from modules where route_path = ?', (route_path,))
            if not row:
                module_ids[feature_key] = db.execute('insert into modules (module_name, route_path, sort_no) values (?, ?, ?)', (module_name, route_path, sort_no)).lastrowid
            else:
                module_ids[feature_key] = row['id']
                db.execute('update modules set module_name = ?, sort_no = ? where id = ?', (module_name, sort_no, row['id']))
        permission_refs = []
        for feature_key, definitions in DEFAULT_PERMISSIONS.items():
            module_id = module_ids[feature_key]
            for permission_key, permission_name, permission_group, sort_no in definitions:
                row = db.fetchone('select id from permissions where module_id = ? and sort_no = ?', (module_id, sort_no))
                if not row:
                    permission_id = db.execute('insert into permissions (module_id, permission_name, permission_group, sort_no) values (?, ?, ?, ?)', (module_id, permission_name, permission_group, sort_no)).lastrowid
                else:
                    permission_id = row['id']
                    db.execute('update permissions set permission_name = ?, permission_group = ? where id = ?', (permission_name, permission_group, permission_id))
                permission_refs.append((feature_key, permission_id, permission_key, permission_group))
        for role in roles:
            role_key = role_key_from_name(role.get('role_name'))
            for feature_key, permission_id, permission_key, permission_group in permission_refs:
                row = db.fetchone('select id, state from role_permissions where role_id = ? and permission_id = ?', (role['id'], permission_id))
                desired_state = _compute_default_state(role_key, feature_key, permission_key)
                if not row:
                    db.execute('insert into role_permissions (role_id, permission_id, state, update_time) values (?, ?, ?, ?)', (role['id'], permission_id, desired_state, '2026-04-24 10:00:00'))
        db.commit()
        _catalog_ready = True
