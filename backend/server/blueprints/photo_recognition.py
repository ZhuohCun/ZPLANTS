from flask import Blueprint, request, g, current_app
from server.auth import auth_required, has_feature_permission
from server.errors import ApiError
from server.db import get_db
from server.responses import success, fail, now_string, to_display_datetime
from server.logger import append_log
from server.common import FEATURE_TO_MODULE_ID
from server.utils import save_upload, save_base64_upload, build_image_url, paginate, fetch_species_for_model, choose_recognition, fetch_species_detail, filter_species_detail_by_permissions


def _normalize_cluster_id(cluster_id, fallback_index=1):
    text_value = str(cluster_id or '').strip()
    if text_value:
        return text_value
    safe_index = max(1, int(fallback_index or 1))
    return f'cluster-{safe_index:02d}'


photo_recognition_bp = Blueprint('photo_recognition', __name__)


@photo_recognition_bp.post('/create')
@auth_required()
def create_recognition():
    image_file = request.files.get('image') or request.files.get('file')
    image_base64 = request.form.get('imageBase64', '')
    if image_file is None and not image_base64:
        return fail(1100, 'Upload a picture.')
    try:
        if image_file is not None:
            filename, image_path = save_upload(image_file, current_app.config['UPLOAD_FOLDER'], 'recognitions')
            image_url = build_image_url(filename)
            source_name = image_file.filename or filename
        else:
            filename, image_path = save_base64_upload(image_base64, current_app.config['UPLOAD_FOLDER'], 'recognitions')
            image_url = build_image_url(filename)
            source_name = filename
    except ApiError as error:
        return fail(error.code, error.message)
    species_rows = fetch_species_for_model()
    try:
        target, topk = choose_recognition(species_rows, filename=source_name, image_path=image_path, topk=current_app.config['MODEL_TOPK'])
    except ApiError as error:
        return fail(error.code, error.message, error.status)
    except Exception as error:
        return fail(1105, 'Recognition failed. Please try again later.')
    db = get_db()
    cursor = db.execute('insert into recognitions (user_id, species_id, image_url, create_time) values (?, ?, ?, ?)', (g.current_user['id'], target['id'], image_url, now_string()))
    recognition_id = cursor.lastrowid
    for idx, item in enumerate(topk, start=1):
        db.execute('insert into recognition_candidates (recognition_id, species_id, confidence, cluster_id) values (?, ?, ?, ?)', (recognition_id, item['speciesId'], item['confidence'], _normalize_cluster_id(item.get('clusterId'), idx)))
    db.commit()
    append_log(g.current_user, 'Submit Recognition', '/api/recognitions', 'POST', FEATURE_TO_MODULE_ID['recognition'])
    return success({'recordId': recognition_id}, 'Recognition completed')


@photo_recognition_bp.get('/list')
@auth_required()
def list_recognitions():
    db = get_db()
    keyword = (request.args.get('speciesName') or request.args.get('plantName') or '').strip()
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)
    user = g.current_user
    sql = '''select r.id, r.user_id, s.species_name, r.create_time, r.image_url
             from recognitions r
             left join species s on r.species_id = s.id and s.is_deleted = 0
             where 1 = 1'''
    params = []
    if user.get('role') != 'admin':
        sql += ' and r.user_id = ?'
        params.append(user['id'])
    sql += ' order by r.id desc'
    rows = db.fetchall(sql, tuple(params))
    result = []
    for row in rows:
        if keyword and keyword not in (row.get('species_name') or ''):
            continue
        result.append({'id': row['id'], 'speciesName': row.get('species_name', ''), 'plantName': row.get('species_name', ''), 'createTime': to_display_datetime(row.get('create_time', '')), 'imageUrl': row.get('image_url', '')})
    return success(paginate(result, page_num, page_size), 'Loaded')


@photo_recognition_bp.get('/options')
@auth_required()
def recognition_options():
    db = get_db()
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)
    keyword = (request.args.get('keyword') or '').strip()
    user = g.current_user
    sql = '''select r.id, s.species_name, r.create_time
             from recognitions r
             left join species s on r.species_id = s.id and s.is_deleted = 0
             where 1 = 1'''
    params = []
    if user.get('role') != 'admin':
        sql += ' and r.user_id = ?'
        params.append(user['id'])
    sql += ' order by r.id desc'
    rows = db.fetchall(sql, tuple(params))
    result = []
    for row in rows:
        label = f"{row.get('species_name', '')} {to_display_datetime(row.get('create_time', ''))}".strip()
        if keyword and keyword not in label:
            continue
        result.append({'id': row['id'], 'label': label})
    return success(paginate(result, page_num, page_size), 'Loaded')


@photo_recognition_bp.get('/detail/<int:record_id>')
@auth_required()
def recognition_detail(record_id):
    db = get_db()
    row = db.fetchone('select * from recognitions where id = ?', (record_id,))
    if not row:
        return fail(1102, 'The recognition record was not found.')
    user = g.current_user
    if user.get('role') != 'admin' and row['user_id'] != user['id']:
        return fail(1103, 'You cannot view this recognition record.', 403)
    species = fetch_species_detail(row['species_id'])
    species = filter_species_detail_by_permissions(species, can_view_distribution=has_feature_permission(g.current_user, 'species', 'view_distribution'), can_view_plants=has_feature_permission(g.current_user, 'plant', 'view')) if species else None
    candidates = db.fetchall('select c.confidence, c.cluster_id, s.id as species_id, s.species_name from recognition_candidates c left join species s on c.species_id = s.id and s.is_deleted = 0 where c.recognition_id = ? order by c.confidence desc, c.id asc', (record_id,))
    topk = [{'speciesId': item.get('species_id'), 'plantId': item.get('species_id'), 'speciesName': item.get('species_name', ''), 'plantName': item.get('species_name', ''), 'confidence': float(item.get('confidence', 0)), 'clusterId': _normalize_cluster_id(item.get('cluster_id', ''), index + 1), 'rank': index + 1} for index, item in enumerate(candidates)]
    primary_cluster_id = topk[0].get('clusterId') if topk else _normalize_cluster_id(None, 1)
    data = {'id': row['id'], 'speciesName': species.get('speciesName', '') if species else '', 'plantName': species.get('speciesName', '') if species else '', 'imageUrl': row.get('image_url', ''), 'createTime': to_display_datetime(row.get('create_time', '')), 'clusterId': primary_cluster_id, 'topK': topk, 'plantInfo': species}
    return success(data, 'Loaded')
