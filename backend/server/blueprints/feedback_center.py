from flask import Blueprint, request, g
from server.auth import auth_required
from server.db import get_db
from server.responses import success, fail, now_string, to_display_datetime
from server.logger import append_log
from server.utils import paginate
from server.common import FEEDBACK_STATUS_TEXT, FEEDBACK_TYPE_TEXT, resolve_feedback_type_id

feedback_center_bp = Blueprint('feedback_center', __name__)


def serialize_feedback(row):
    return {
        'id': row['id'],
        'userId': row.get('user_id'),
        'username': row.get('username', ''),
        'type': row.get('type_name', '') or FEEDBACK_TYPE_TEXT.get(int(row.get('feedback_type_id') or 0), ''),
        'typeCode': int(row.get('feedback_type_id') or 0),
        'content': row.get('content', ''),
        'recognitionId': row.get('recognition_id') or '',
        'recognitionLabel': row.get('recognition_label', ''),
        'status': FEEDBACK_STATUS_TEXT.get(int(row.get('audit_state') or 0), ''),
        'statusCode': int(row.get('audit_state') or 0),
        'auditRemark': row.get('audit_remark', ''),
        'createTime': to_display_datetime(row.get('create_time', '')),
        'auditTime': to_display_datetime(row.get('audit_time', '')),
        'auditedBy': row.get('audited_by_name', ''),
    }


def _base_feedback_query():
    return '''select f.*, u.username, ft.type_name, au.real_name as audited_by_name,
                     concat('#', r.id, ' ', coalesce(ps.species_name, ''), ' ', coalesce(r.create_time, '')) as recognition_label
              from feedbacks f
              left join users u on f.user_id = u.id
              left join feedback_types ft on f.feedback_type_id = ft.id
              left join users au on f.audited_by_user_id = au.id
              left join recognitions r on f.recognition_id = r.id
              left join species ps on r.species_id = ps.id and ps.is_deleted = 0
              where 1 = 1'''


@feedback_center_bp.post('/submit')
@auth_required()
def create_feedback():
    payload = request.get_json(silent=True) or {}
    feedback_type_id = resolve_feedback_type_id(payload.get('typeCode') or payload.get('type') or 1)
    content = (payload.get('content') or '').strip()
    recognition_id = payload.get('recognitionId') or None
    if not content:
        return fail(1301, 'Enter feedback content.')
    db = get_db()
    if recognition_id:
        row = db.fetchone('select id from recognitions where id = ?', (recognition_id,))
        if not row:
            return fail(1302, 'The recognition record was not found.')
    cursor = db.execute(
        'insert into feedbacks (user_id, feedback_type_id, recognition_id, content, audit_state, audit_remark, create_time, audit_time, audited_by_user_id) values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (g.current_user['id'], feedback_type_id, recognition_id, content, 1, '', now_string(), None, None),
    )
    db.commit()
    append_log(g.current_user, 'Send Feedback', '/api/feedbacks', 'POST', 7)
    return success({'id': cursor.lastrowid}, 'Sent')


@feedback_center_bp.get('/types')
@auth_required()
def list_feedback_types():
    return success([{'code': key, 'id': key, 'name': value} for key, value in FEEDBACK_TYPE_TEXT.items()], 'Loaded')


@feedback_center_bp.get('/my')
@auth_required()
def my_feedbacks():
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)
    rows = get_db().fetchall(_base_feedback_query() + ' and f.user_id = ? order by f.id desc', (g.current_user['id'],))
    return success(paginate([serialize_feedback(row) for row in rows], page_num, page_size), 'Loaded')


@feedback_center_bp.get('/list')
@auth_required()
def list_feedbacks():
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)
    status = request.args.get('status')
    rows = get_db().fetchall(_base_feedback_query() + ' order by f.id desc')
    data = []
    for row in rows:
        if status not in [None, '', 'all'] and int(row.get('audit_state') or 0) != int(status):
            continue
        data.append(serialize_feedback(row))
    return success(paginate(data, page_num, page_size), 'Loaded')


@feedback_center_bp.post('/audit/<int:feedback_id>')
@auth_required()
def audit_feedback(feedback_id):
    payload = request.get_json(silent=True) or {}
    status = int(payload.get('auditStatus') or 2)
    if status not in [2, 3]:
        return fail(1303, 'The review status is not valid.')
    db = get_db()
    row = db.fetchone('select id from feedbacks where id = ?', (feedback_id,))
    if not row:
        return fail(1304, 'The feedback item was not found.')
    db.execute(
        'update feedbacks set audit_state = ?, audit_remark = ?, audit_time = ?, audited_by_user_id = ? where id = ?',
        (status, payload.get('auditRemark', ''), now_string(), g.current_user['id'], feedback_id),
    )
    db.commit()
    append_log(g.current_user, 'Review Feedback', f'/api/feedbacks/{feedback_id}/audit', 'POST', 7)
    return success({}, 'Reviewed')
