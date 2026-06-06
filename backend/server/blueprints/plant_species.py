
import json
from flask import Blueprint, g, request, current_app

from server.auth import auth_required, has_feature_permission
from server.common import FEATURE_TO_MODULE_ID
from server.db import get_db
from server.logger import append_log
from server.blueprints.care_reminder_engine import run_care_reminder_engine
from server.responses import fail, now_string, success
from server.utils import fetch_species_detail, filter_species_detail_by_permissions, replace_species_image, save_upload, build_image_url
from server.cache import invalidate_namespaces, redis_remember_json

plant_species_bp = Blueprint('plant_species', __name__)


def _clear_species_cache():
    invalidate_namespaces('species_list', 'species_detail', 'plant_list', 'plant_detail', 'model_species')


def _species_rule_rows_for_update(db, species_id):
    if getattr(db, 'driver', '') == 'mysql':
        db.fetchone('select id from species where id = ? and is_deleted = 0 for update', (species_id,))
        return db.fetchall(
            '''select cr.id as rule_id, cr.species_id, cr.is_deleted, cr.care_method_id, cr.cycle_days
               from care_rules cr
               where cr.species_id = ?
               order by cr.is_deleted asc, cr.id asc for update''',
            (species_id,),
        )
    return db.fetchall(
        '''select cr.id as rule_id, cr.species_id, cr.is_deleted, cr.care_method_id, cr.cycle_days
           from care_rules cr
           where cr.species_id = ?
           order by cr.is_deleted asc, cr.id asc''',
        (species_id,),
    )


def serialize_species(row, rule_map, can_view_distribution=True):
    return {
        'id': row['id'],
        'speciesName': row.get('species_name', ''),
        'scientificName': row.get('scientific_name', ''),
        'lightRequirement': row.get('light_requirement', ''),
        'distribution': row.get('distribution', '') if can_view_distribution else '',
        'careRules': rule_map.get(row['id'], []),
        'care_rules': rule_map.get(row['id'], []),
        'imageUrl': row.get('image_url', ''),
        'plantCount': int(row.get('plant_count') or 0),
    }


def _parse_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    payload = dict(request.form or {})
    rules = payload.get('careRules') or payload.get('care_rules') or '[]'
    if isinstance(rules, str):
        try:
            parsed = json.loads(rules)
        except Exception:
            parsed = []
    else:
        parsed = rules
    payload['careRules'] = parsed
    payload['care_rules'] = parsed
    return payload


def _parse_cycle_days(value):
    text = str(value or '').strip()
    if not text or not text.isdigit() or int(text) <= 0:
        return 0
    return int(text)


def _validate_species_rules(db, rules):
    cleaned = []
    seen_method_ids = set()
    for index, rule in enumerate(rules or [], start=1):
        method_id = int(rule.get('careMethodId') or 0)
        cycle_days = _parse_cycle_days(rule.get('cycleDays'))
        if not method_id and cycle_days == 0:
            continue
        if not method_id:
            return False, f'No.{index}care rule has no selected method', []
        if cycle_days <= 0:
            return False, f'No.{index}care rule must use a positive whole-number cycle', []
        if method_id in seen_method_ids:
            return False, 'The same care rule already exists.', []
        method = db.fetchone('select id from care_methods where id = ? and is_deleted = 0', (method_id,))
        if not method:
            return False, f'No.{index}care rule refers to a method that no longer exists', []
        cleaned.append({'careMethodId': method_id, 'cycleDays': cycle_days})
        seen_method_ids.add(method_id)
    return True, '', cleaned


def _save_species_rules(db, species_id, rules):
    now = now_string()
    rows = _species_rule_rows_for_update(db, species_id)
    existing_by_method = {int(row.get('care_method_id') or 0): row for row in rows if row.get('care_method_id')}
    keep_rule_ids = set()
    for rule in rules:
        desired_method_id = int(rule['careMethodId'])
        desired_cycle_days = int(rule['cycleDays'])
        target_row = existing_by_method.get(desired_method_id)
        if target_row is None:
            cur = db.execute(
                'insert into care_rules (species_id, care_method_id, cycle_days, create_time, update_time, is_deleted) values (?, ?, ?, ?, ?, 0)',
                (species_id, desired_method_id, desired_cycle_days, now, now),
            )
            keep_rule_ids.add(int(cur.lastrowid))
            continue
        if int(target_row.get('cycle_days') or 0) != desired_cycle_days or int(target_row.get('is_deleted') or 0) == 1:
            db.execute(
                'update care_rules set cycle_days = ?, update_time = ?, is_deleted = 0 where id = ? and species_id = ?',
                (desired_cycle_days, now, target_row['rule_id'], species_id),
            )
        keep_rule_ids.add(int(target_row['rule_id']))
    for row in rows:
        if int(row.get('rule_id') or 0) in keep_rule_ids:
            continue
        if int(row.get('is_deleted') or 0) == 0:
            db.execute('update care_rules set is_deleted = 1, update_time = ? where id = ? and species_id = ?', (now, row['rule_id'], species_id))


@plant_species_bp.get('/list')
@auth_required()
def list_species():
    keyword = (request.args.get('keyword') or '').strip()
    page_num = max(int(request.args.get('pageNum', 1) or 1), 1)
    page_size = max(int(request.args.get('pageSize', 5) or 5), 1)
    can_view_distribution = has_feature_permission(g.current_user, 'species', 'view_distribution')

    def producer():
        db = get_db()
        rows = db.fetchall('select s.id, s.species_name, s.scientific_name, s.light_requirement from species s where s.is_deleted = 0 order by s.id asc')
        filtered_rows = []
        for row in rows:
            text_value = f"{row.get('species_name', '')}{row.get('scientific_name', '')}"
            if keyword and keyword not in text_value:
                continue
            filtered_rows.append(dict(row))
        start = (page_num - 1) * page_size
        page_slice = filtered_rows[start:start + page_size]
        species_ids = [row['id'] for row in page_slice]
        distribution_map, rule_map, image_map, plant_count_map = {}, {}, {}, {}
        if species_ids:
            placeholders = ','.join(['?'] * len(species_ids))
            distribution_rows = db.fetchall(
                f'''select p.species_id, z.zone_name, l.location_name
                    from plants p
                    left join locations l on p.location_id = l.id and l.is_deleted = 0
                    left join campus_zones z on l.zone_id = z.id and z.is_deleted = 0
                    where p.species_id in ({placeholders}) and p.is_deleted = 0
                    order by p.species_id asc, z.zone_name asc, l.location_name asc''',
                tuple(species_ids),
            )
            plant_count_rows = db.fetchall(
                f'''select species_id, count(*) as plant_count
                    from plants
                    where species_id in ({placeholders}) and is_deleted = 0
                    group by species_id''',
                tuple(species_ids),
            )
            for item in distribution_rows:
                zone_name = item.get('zone_name') or ''
                location_name = item.get('location_name') or ''
                text = f'{zone_name} - {location_name}' if zone_name else location_name
                if text:
                    distribution_map.setdefault(item['species_id'], [])
                    if text not in distribution_map[item['species_id']]:
                        distribution_map[item['species_id']].append(text)
            for item in plant_count_rows:
                plant_count_map[item['species_id']] = int(item.get('plant_count') or 0)
            rule_rows = db.fetchall(
                f'''select cr.species_id, cr.id, cr.cycle_days, cm.id as care_method_id, cm.method_name
                    from care_rules cr
                    inner join care_methods cm on cr.care_method_id = cm.id and cm.is_deleted = 0
                    where cr.species_id in ({placeholders}) and cr.is_deleted = 0
                    order by cr.id asc''',
                tuple(species_ids),
            )
            for row in rule_rows:
                rule_map.setdefault(row['species_id'], []).append({'id': row['id'], 'careMethodId': row.get('care_method_id'), 'methodName': row.get('method_name', ''), 'cycleDays': row.get('cycle_days') or ''})
            image_rows = db.fetchall(
                f'''select species_id, image_url from species_images where species_id in ({placeholders}) and is_deleted = 0 order by id desc''',
                tuple(species_ids),
            )
            for row in image_rows:
                image_map.setdefault(row['species_id'], row.get('image_url', ''))
        for row in page_slice:
            row['distribution'] = ', '.join(distribution_map.get(row['id'], []))
            row['image_url'] = image_map.get(row['id'], '')
            row['plant_count'] = plant_count_map.get(row['id'], 0)
        return {'list': [serialize_species(row, rule_map, can_view_distribution) for row in page_slice], 'pageNum': page_num, 'pageSize': page_size, 'total': len(filtered_rows), 'totalPages': ((len(filtered_rows) + page_size - 1) // page_size) or 1}

    return success(redis_remember_json('species_list', (keyword, page_num, page_size, can_view_distribution), 90, producer), 'Loaded')


@plant_species_bp.get('/detail/<int:species_id>')
@auth_required()
def detail_species(species_id):
    can_view_distribution = has_feature_permission(g.current_user, 'species', 'view_distribution')
    can_view_plants = has_feature_permission(g.current_user, 'plant', 'view')

    def producer():
        detail = fetch_species_detail(species_id)
        if not detail:
            return None
        return filter_species_detail_by_permissions(detail, can_view_distribution=can_view_distribution, can_view_plants=can_view_plants)

    detail = redis_remember_json('species_detail', (species_id, can_view_distribution, can_view_plants), 90, producer)
    if not detail:
        return fail(1401, 'The plant species was not found.')
    return success(detail, 'Loaded')


@plant_species_bp.post('/create')
@auth_required()
def create_species():
    payload = _parse_payload()
    name = (payload.get('speciesName') or '').strip()
    if not name:
        return fail(1402, 'Enter a plant species name.')
    db = get_db()
    db.begin()
    ok, message, clean_rules = _validate_species_rules(db, payload.get('care_rules') or payload.get('careRules') or [])
    if not ok:
        db.rollback()
        return fail(1405, message)
    if db.fetchone('select id from species where species_name = ? and is_deleted = 0', (name,)):
        db.rollback()
        return fail(1403, 'This plant species already exists.')
    now = now_string()
    cur = db.execute('insert into species (species_name, scientific_name, care_points, light_requirement, create_time, update_time, is_deleted) values (?, ?, ?, ?, ?, ?, 0)', (name, payload.get('scientificName', ''), payload.get('carePoints', ''), payload.get('lightRequirement', ''), now, now))
    species_id = cur.lastrowid
    _save_species_rules(db, species_id, clean_rules)
    image_file = request.files.get('image') or request.files.get('speciesImage')
    if image_file is not None:
        filename, _image_path = save_upload(image_file, current_app.config['UPLOAD_FOLDER'], 'species')
        replace_species_image(species_id, build_image_url(filename))
    db.commit()
    _clear_species_cache()
    run_care_reminder_engine('after-species-save', db=db)
    append_log(g.current_user, 'Add Plant Species', '/api/species', 'POST', FEATURE_TO_MODULE_ID['species'])
    return success(fetch_species_detail(species_id), 'Added')


@plant_species_bp.put('/update/<int:species_id>')
@auth_required()
def update_species(species_id):
    payload = _parse_payload()
    db = get_db()
    db.begin()
    row = db.fetchone('select * from species where id = ? and is_deleted = 0', (species_id,))
    if not row:
        db.rollback()
        return fail(1401, 'The plant species was not found.')
    incoming_rules = payload.get('care_rules') if payload.get('care_rules') is not None else payload.get('careRules')
    if incoming_rules in [None, '']:
        existing_detail = fetch_species_detail(species_id) or {}
        incoming_rules = existing_detail.get('careRules') or existing_detail.get('care_rules') or []
    ok, message, clean_rules = _validate_species_rules(db, incoming_rules)
    if not ok:
        db.rollback()
        return fail(1405, message)
    db.execute('update species set species_name = ?, scientific_name = ?, care_points = ?, light_requirement = ?, update_time = ? where id = ? and is_deleted = 0', (payload.get('speciesName', row.get('species_name', '')), payload.get('scientificName', row.get('scientific_name', '')), payload.get('carePoints', row.get('care_points', '')), payload.get('lightRequirement', row.get('light_requirement', '')), now_string(), species_id))
    _save_species_rules(db, species_id, clean_rules)
    image_file = request.files.get('image') or request.files.get('speciesImage')
    if image_file is not None:
        filename, _image_path = save_upload(image_file, current_app.config['UPLOAD_FOLDER'], 'species')
        replace_species_image(species_id, build_image_url(filename))
    db.commit()
    _clear_species_cache()
    run_care_reminder_engine('after-species-save', db=db)
    append_log(g.current_user, 'Edit Plant Species', f'/api/species/{species_id}', 'PUT', FEATURE_TO_MODULE_ID['species'])
    return success(fetch_species_detail(species_id), 'Updated')


@plant_species_bp.delete('/delete/<int:species_id>')
@auth_required()
def delete_species(species_id):
    db = get_db()
    row = db.fetchone('select * from species where id = ? and is_deleted = 0', (species_id,))
    if not row:
        return fail(1401, 'The plant species was not found.')
    if db.fetchone('select id from plants where species_id = ? and is_deleted = 0 limit 1', (species_id,)):
        return fail(1406, 'This species still has plants. Remove those records before deleting the species.')
    now = now_string()
    db.execute('update care_rules set is_deleted = 1, update_time = ? where species_id = ? and is_deleted = 0', (now, species_id))
    db.execute('update species_images set is_deleted = 1, update_time = ? where species_id = ? and is_deleted = 0', (now, species_id))
    db.execute('update species set is_deleted = 1, update_time = ? where id = ?', (now, species_id))
    db.commit()
    _clear_species_cache()
    run_care_reminder_engine('after-species-delete', db=db)
    append_log(g.current_user, 'Delete Plant Species', f'/api/species/{species_id}', 'DELETE', FEATURE_TO_MODULE_ID['species'])
    return success({}, 'Deleted')
