from flask import Blueprint, g, request

from server.auth import auth_required
from server.db import get_db
from server.logger import append_log
from server.responses import fail, now_string, success
from server.utils import paginate
from server.cache import invalidate_namespaces, redis_remember_json

care_methods_bp = Blueprint('care_methods', __name__)


def _load_care_methods():
    db = get_db()
    rows = db.fetchall('select * from care_methods where is_deleted = 0 order by id asc')
    return [{'id': row['id'], 'methodCode': row['id'], 'methodName': row.get('method_name', '')} for row in rows]


def list_care_methods():
    return redis_remember_json('care_methods', ('all',), 300, _load_care_methods)


def _clear_care_method_cache():
    invalidate_namespaces('care_methods', 'species_list', 'species_detail', 'plant_list', 'plant_detail')


@care_methods_bp.get('/methods/list')
@auth_required()
def list_methods_api():
    keyword = (request.args.get('keyword') or '').strip()
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)

    def producer():
        db = get_db()
        sql = 'select * from care_methods where is_deleted = 0'
        params = []
        if keyword:
            sql += ' and method_name like ?'
            params.append(f'%{keyword}%')
        sql += ' order by id asc'
        rows = db.fetchall(sql, tuple(params))
        data = [{'id': row['id'], 'methodCode': row['id'], 'methodName': row.get('method_name', '')} for row in rows]
        return paginate(data, page_num, page_size)

    return success(redis_remember_json('care_methods', ('list', keyword, page_num, page_size), 300, producer), 'Loaded')


@care_methods_bp.post('/methods/create')
@auth_required()
def create_method_api():
    payload = request.get_json(silent=True) or {}
    name = (payload.get('methodName') or '').strip()
    if not name:
        return fail(1206, 'Enter a care method name.')
    db = get_db()
    exists = db.fetchone('select id from care_methods where method_name = ? and is_deleted = 0', (name,))
    if exists:
        return fail(1207, 'A care method with this name already exists.')
    deleted_row = db.fetchone('select id from care_methods where method_name = ? and is_deleted = 1', (name,))
    now = now_string()
    if deleted_row:
        db.execute('update care_methods set is_deleted = 0, update_time = ? where id = ?', (now, deleted_row['id']))
        method_id = deleted_row['id']
    else:
        cur = db.execute('insert into care_methods (method_name, create_time, update_time, is_deleted) values (?, ?, ?, 0)', (name, now, now))
        method_id = cur.lastrowid
    db.commit()
    _clear_care_method_cache()
    append_log(g.current_user, 'Add Care Method', '/api/care/methods', 'POST', 6)
    row = db.fetchone('select * from care_methods where id = ? and is_deleted = 0', (method_id,))
    return success({'id': row['id'], 'methodCode': row['id'], 'methodName': row.get('method_name', '')}, 'Saved')


@care_methods_bp.put('/methods/update/<int:method_id>')
@auth_required()
def update_method_api(method_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    row = db.fetchone('select * from care_methods where id = ? and is_deleted = 0', (method_id,))
    if not row:
        return fail(1208, 'The care method was not found.')
    name = (payload.get('methodName') or row.get('method_name', '')).strip()
    if not name:
        return fail(1206, 'Enter a care method name.')
    duplicate = db.fetchone('select id from care_methods where method_name = ? and id <> ? and is_deleted = 0', (name, method_id))
    if duplicate:
        return fail(1207, 'A care method with this name already exists.')
    db.execute('update care_methods set method_name = ?, update_time = ? where id = ? and is_deleted = 0', (name, now_string(), method_id))
    db.commit()
    _clear_care_method_cache()
    append_log(g.current_user, 'Edit Care Method', f'/api/care/methods/{method_id}', 'PUT', 6)
    return success({}, 'Updated')


@care_methods_bp.delete('/methods/delete/<int:method_id>')
@auth_required()
def delete_method_api(method_id):
    db = get_db()
    row = db.fetchone('select id from care_methods where id = ? and is_deleted = 0', (method_id,))
    if not row:
        return fail(1208, 'The care method was not found.')
    if db.fetchone('select id from care_rules where care_method_id = ? and is_deleted = 0 limit 1', (method_id,)):
        return fail(1209, 'This care method is still used by a care rule and cannot be deleted.')
    db.execute('update care_methods set is_deleted = 1, update_time = ? where id = ? and is_deleted = 0', (now_string(), method_id))
    db.commit()
    _clear_care_method_cache()
    append_log(g.current_user, 'Delete Care Method', f'/api/care/methods/{method_id}', 'DELETE', 6)
    return success({}, 'Deleted')


