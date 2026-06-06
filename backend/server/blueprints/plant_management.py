
from flask import Blueprint, g, request

from server.auth import auth_required, has_feature_permission
from server.db import get_db
from server.logger import append_log
from server.responses import fail, now_string, success
from server.blueprints.care_reminder_engine import run_care_reminder_engine
from server.utils import fetch_species_image, filter_plant_detail_by_permissions, filter_plant_list_by_permissions
from server.cache import invalidate_namespaces, redis_remember_json

plant_management_bp = Blueprint('plant_management', __name__)


def _clear_plant_cache():
    invalidate_namespaces('plant_list', 'plant_detail', 'species_list', 'species_detail', 'locations')


def fetch_plant_species(plant_id):
    db = get_db()
    row = db.fetchone(
        """select s.*
           from plants p
           left join species s on p.species_id = s.id and s.is_deleted = 0
           where p.id = ? and p.is_deleted = 0""",
        (plant_id,),
    )
    return [row] if row else []


def fetch_plant_locations(plant_id):
    db = get_db()
    row = db.fetchone(
        """select l.id as location_id, l.location_name, z.id as zone_id, z.zone_name
           from plants p
           left join locations l on p.location_id = l.id and l.is_deleted = 0
           left join campus_zones z on l.zone_id = z.id and z.is_deleted = 0
           where p.id = ? and p.is_deleted = 0""",
        (plant_id,),
    )
    return [row] if row else []


def build_distribution(rows):
    texts = []
    for row in rows:
        zone_name = row.get('zone_name') or ''
        location_name = row.get('location_name') or ''
        value = f'{zone_name} - {location_name}' if zone_name else location_name
        if value and value not in texts:
            texts.append(value)
    return ', '.join(texts)


def _display_name(species_name, zone_name, location_name, plant_id):
    text = ' '.join(part for part in [species_name, f'{zone_name} - {location_name}' if zone_name and location_name else zone_name or location_name] if part)
    return text or f'Plant{plant_id}'


def _rule_map_for_species_ids(species_ids):
    db = get_db()
    if not species_ids:
        return {}
    placeholders = ','.join(['?'] * len(species_ids))
    rows = db.fetchall(
        f"""select cr.species_id, cr.id, cr.cycle_days, cm.id as care_method_id, cm.method_name
            from care_rules cr
            inner join care_methods cm on cr.care_method_id = cm.id and cm.is_deleted = 0
            where cr.species_id in ({placeholders}) and cr.is_deleted = 0
            order by cr.id asc""",
        tuple(species_ids),
    )
    rule_map = {}
    for row in rows:
        rule_map.setdefault(row['species_id'], []).append({
            'id': row['id'],
            'careMethodId': row.get('care_method_id'),
            'methodName': row.get('method_name', ''),
            'cycleDays': row.get('cycle_days') or '',
        })
    return rule_map


def serialize_plant(row, rule_map=None):
    rule_map = rule_map or {}
    species_id = row.get('species_id')
    return {
        'id': row['id'],
        'displayName': _display_name(row.get('species_name', ''), row.get('zone_name', ''), row.get('location_name', ''), row['id']),
        'speciesId': species_id,
        'speciesName': row.get('species_name', ''),
        'scientificName': row.get('scientific_name', ''),
        'distribution': row.get('distribution', ''),
        'locations': row.get('locations', []),
        'coverImage': row.get('cover_image') or '/uploads/plants/default-cover.png',
        'careRules': rule_map.get(species_id, []),
        'care_rules': rule_map.get(species_id, []),
    }


def serialize_plant_detail(plant_id):
    db = get_db()
    row = db.fetchone('select * from plants where id = ? and is_deleted = 0', (plant_id,))
    if not row:
        return None
    species_rows = fetch_plant_species(plant_id)
    location_rows = fetch_plant_locations(plant_id)
    species_row = species_rows[0] if species_rows else {}
    rule_map = _rule_map_for_species_ids([species_row.get('id')]) if species_row.get('id') else {}
    care_rules = rule_map.get(species_row.get('id'), [])
    first_location = location_rows[0] if location_rows else {}
    return {
        'id': row['id'],
        'displayName': _display_name(species_row.get('species_name', ''), first_location.get('zone_name', ''), first_location.get('location_name', ''), row['id']),
        'speciesId': species_row.get('id'),
        'speciesName': species_row.get('species_name', ''),
        'scientificName': species_row.get('scientific_name', ''),
        'carePoints': species_row.get('care_points', ''),
        'lightRequirement': species_row.get('light_requirement', ''),
        'distribution': build_distribution(location_rows),
        'locations': location_rows,
        'coverImage': fetch_species_image(species_row.get('id')) or '/uploads/plants/default-cover.png',
        'careRules': care_rules,
        'care_rules': care_rules,
    }


@plant_management_bp.get('/list')
@auth_required()
def list_plants():
    keyword = (request.args.get('keyword') or '').strip()
    zone_id = (request.args.get('zoneId') or '').strip()
    species_id = (request.args.get('speciesId') or '').strip()
    page_num = max(int(request.args.get('pageNum', 1) or 1), 1)
    page_size = max(int(request.args.get('pageSize', 5) or 5), 1)
    can_view_distribution = has_feature_permission(g.current_user, 'species', 'view_distribution')

    def producer():
        rows = get_db().fetchall(
            """select p.id, p.species_id, s.species_name, s.scientific_name,
                      coalesce(si.image_url, '/uploads/plants/default-cover.png') as cover_image,
                      z.id as zone_id, z.zone_name, l.id as location_id, l.location_name
               from plants p
               left join species s on p.species_id = s.id and s.is_deleted = 0
               left join locations l on p.location_id = l.id and l.is_deleted = 0
               left join campus_zones z on l.zone_id = z.id and z.is_deleted = 0
               left join species_images si on s.id = si.species_id and si.is_deleted = 0
               where p.is_deleted = 0
               order by p.id asc"""
        )
        filtered_rows = []
        for row in rows:
            text_value = f"{row.get('species_name', '')}{row.get('zone_name', '')}{row.get('location_name', '')}"
            if keyword and keyword not in text_value:
                continue
            if species_id not in ['', 'all', None] and int(row.get('species_id') or 0) != int(species_id):
                continue
            if zone_id not in ['', 'all', None] and int(row.get('zone_id') or 0) != int(zone_id):
                continue
            item = dict(row)
            zone_name = item.get('zone_name') or ''
            location_name = item.get('location_name') or ''
            item['distribution'] = f'{zone_name} - {location_name}' if zone_name else location_name
            item['locations'] = []
            if item.get('zone_id') or item.get('location_name'):
                item['locations'].append({
                    'zone_id': item.get('zone_id'),
                    'zone_name': zone_name,
                    'location_id': item.get('location_id'),
                    'location_name': location_name,
                    'zoneId': item.get('zone_id'),
                    'zoneName': zone_name,
                    'locationId': item.get('location_id'),
                    'locationName': location_name,
                })
            filtered_rows.append(item)
        start_index = (page_num - 1) * page_size
        page_rows = filtered_rows[start_index:start_index + page_size]
        species_ids = sorted({row.get('species_id') for row in page_rows if row.get('species_id')})
        rule_map = _rule_map_for_species_ids(species_ids)
        result = [serialize_plant(row, rule_map) for row in page_rows]
        result = filter_plant_list_by_permissions(result, can_view_distribution=can_view_distribution)
        return {'records': result, 'list': result, 'total': len(filtered_rows), 'pageNum': page_num, 'pageSize': page_size}

    return success(redis_remember_json('plant_list', (keyword, zone_id, species_id, page_num, page_size, can_view_distribution), 90, producer), 'Loaded')


@plant_management_bp.get('/detail/<int:plant_id>')
@auth_required()
def get_plant(plant_id):
    can_view_distribution = has_feature_permission(g.current_user, 'species', 'view_distribution')

    def producer():
        detail = serialize_plant_detail(plant_id)
        if not detail:
            return None
        return filter_plant_detail_by_permissions(detail, can_view_distribution=can_view_distribution)

    detail = redis_remember_json('plant_detail', (plant_id, can_view_distribution), 90, producer)
    if not detail:
        return fail(1501, 'The plant was not found.')
    return success(detail, 'Loaded')


@plant_management_bp.post('/create')
@auth_required()
def create_plant():
    payload = request.get_json(silent=True) or request.form or {}
    species_id = payload.get('speciesId')
    if request.is_json:
        location_ids = payload.get('locationIds') or []
    else:
        location_ids = request.form.getlist('locationIds') or ([request.form.get('locationIds')] if request.form.get('locationIds') else [])
    if not species_id or not location_ids:
        return fail(1502, 'Choose a plant species and a location.')
    db = get_db()
    species_row = db.fetchone('select id from species where id = ? and is_deleted = 0', (int(species_id),))
    location_row = db.fetchone('select id from locations where id = ? and is_deleted = 0', (int(location_ids[0]),))
    if not species_row or not location_row:
        return fail(1504, 'The selected plant species or location was not found.')
    now = now_string()
    cursor = db.execute('insert into plants (species_id, location_id, create_time, update_time, is_deleted) values (?, ?, ?, ?, 0)', (int(species_id), int(location_ids[0]), now, now))
    plant_id = cursor.lastrowid
    db.commit()
    _clear_plant_cache()
    run_care_reminder_engine('after-plant-create', db=db)
    append_log(g.current_user, 'Add Plant', '/api/plants', 'POST', 5)
    return success(serialize_plant_detail(plant_id), 'Added')


@plant_management_bp.put('/update/<int:plant_id>')
@auth_required()
def update_plant(plant_id):
    payload = request.get_json(silent=True) or request.form or {}
    db = get_db()
    row = db.fetchone('select * from plants where id = ? and is_deleted = 0', (plant_id,))
    if not row:
        return fail(1501, 'The plant was not found.')
    species_id = payload.get('speciesId')
    if request.is_json:
        location_ids = payload.get('locationIds') or []
    else:
        location_ids = request.form.getlist('locationIds') or ([request.form.get('locationIds')] if request.form.get('locationIds') else [])
    if not species_id or not location_ids:
        return fail(1502, 'Choose a plant species and a location.')
    species_row = db.fetchone('select id from species where id = ? and is_deleted = 0', (int(species_id),))
    location_row = db.fetchone('select id from locations where id = ? and is_deleted = 0', (int(location_ids[0]),))
    if not species_row or not location_row:
        return fail(1504, 'The selected plant species or location was not found.')
    db.execute('update plants set species_id = ?, location_id = ?, update_time = ? where id = ? and is_deleted = 0', (int(species_id), int(location_ids[0]), now_string(), plant_id))
    db.commit()
    _clear_plant_cache()
    run_care_reminder_engine('after-plant-update', db=db)
    append_log(g.current_user, 'Edit Plant', f'/api/plants/{plant_id}', 'PUT', 5)
    return success(serialize_plant_detail(plant_id), 'Updated')


@plant_management_bp.delete('/delete/<int:plant_id>')
@auth_required()
def delete_plant(plant_id):
    db = get_db()
    row = db.fetchone('select * from plants where id = ? and is_deleted = 0', (plant_id,))
    if not row:
        return fail(1501, 'The plant was not found.')
    now = now_string()
    db.execute('update plants set is_deleted = 1, update_time = ? where id = ? and is_deleted = 0', (now, plant_id))
    db.commit()
    _clear_plant_cache()
    run_care_reminder_engine('after-plant-delete', db=db)
    append_log(g.current_user, 'Delete Plant', f'/api/plants/{plant_id}', 'DELETE', 5)
    return success({}, 'Deleted')
