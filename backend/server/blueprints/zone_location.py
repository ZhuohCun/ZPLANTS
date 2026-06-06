from flask import Blueprint, g, request

from server.auth import auth_required
from server.db import get_db
from server.logger import append_log
from server.responses import fail, now_string, success
from server.cache import invalidate_namespaces, redis_remember_json

location_bp = Blueprint('zone_location', __name__)


def serialize_zone(row):
    return {'id': row['id'], 'zoneName': row.get('zone_name', ''), 'locationCount': int(row.get('location_count') or 0)}


def serialize_location(row):
    return {'id': row['id'], 'zoneId': row.get('zone_id'), 'locationName': row.get('location_name', '')}


def _clear_location_cache():
    invalidate_namespaces('locations', 'species_list', 'species_detail', 'plant_list', 'plant_detail')


@location_bp.get('/zones/list')
@auth_required()
def list_zones():
    def producer():
        rows = get_db().fetchall(
            """select z.*, count(l.id) as location_count
               from campus_zones z
               left join locations l on l.zone_id = z.id and l.is_deleted = 0
               where z.is_deleted = 0
               group by z.id
               order by z.id asc"""
        )
        return [serialize_zone(row) for row in rows]

    return success(redis_remember_json('locations', ('zones',), 300, producer), 'Loaded')


@location_bp.post('/zones/create')
@auth_required()
def create_zone():
    payload = request.get_json(silent=True) or {}
    zone_name = (payload.get('zoneName') or '').strip()
    if not zone_name:
        return fail(1401, 'Enter a zone name.')
    db = get_db()
    exists = db.fetchone('select id from campus_zones where zone_name = ? and is_deleted = 0', (zone_name,))
    if exists:
        return fail(1402, 'A zone with this name already exists.')
    cur = db.execute('insert into campus_zones (zone_name, create_time, update_time, is_deleted) values (?, ?, ?, 0)', (zone_name, now_string(), now_string()))
    db.commit()
    _clear_location_cache()
    append_log(g.current_user, 'Add Zone', '/api/locations/zones', 'POST', 10)
    row = db.fetchone('select *, 0 as location_count from campus_zones where id = ? and is_deleted = 0', (cur.lastrowid,))
    return success(serialize_zone(row), 'Saved')


@location_bp.put('/zones/update/<int:zone_id>')
@auth_required()
def update_zone(zone_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    row = db.fetchone('select * from campus_zones where id = ? and is_deleted = 0', (zone_id,))
    if not row:
        return fail(1403, 'The zone was not found.')
    zone_name = (payload.get('zoneName') or row.get('zone_name') or '').strip()
    if not zone_name:
        return fail(1401, 'Enter a zone name.')
    duplicate = db.fetchone('select id from campus_zones where zone_name = ? and id <> ? and is_deleted = 0', (zone_name, zone_id))
    if duplicate:
        return fail(1402, 'A zone with this name already exists.')
    db.execute('update campus_zones set zone_name = ?, update_time = ?, is_deleted = 0 where id = ?', (zone_name, now_string(), zone_id))
    db.commit()
    _clear_location_cache()
    append_log(g.current_user, 'Edit Zone', f'/api/locations/zones/{zone_id}', 'PUT', 10)
    result = db.fetchone("""select z.*, count(l.id) as location_count from campus_zones z left join locations l on l.zone_id = z.id and l.is_deleted = 0 where z.id = ? and z.is_deleted = 0 group by z.id""", (zone_id,))
    return success(serialize_zone(result), 'Updated')


@location_bp.delete('/zones/delete/<int:zone_id>')
@auth_required()
def delete_zone(zone_id):
    db = get_db()
    row = db.fetchone('select id from campus_zones where id = ? and is_deleted = 0', (zone_id,))
    if not row:
        return fail(1403, 'The zone was not found.')
    if db.fetchone('select id from locations where zone_id = ? and is_deleted = 0 limit 1', (zone_id,)):
        return fail(1404, 'This zone still contains locations and cannot be deleted.')
    db.execute('update campus_zones set is_deleted = 1, update_time = ? where id = ?', (now_string(), zone_id))
    db.commit()
    _clear_location_cache()
    append_log(g.current_user, 'Delete Zone', f'/api/locations/zones/{zone_id}', 'DELETE', 10)
    return success({}, 'Deleted')


@location_bp.get('/zones/<int:zone_id>/locations/list')
@auth_required()
def list_zone_locations(zone_id):
    def producer():
        rows = get_db().fetchall('select * from locations where zone_id = ? and is_deleted = 0 order by id asc', (zone_id,))
        return [serialize_location(row) for row in rows]

    return success(redis_remember_json('locations', ('zone-locations', zone_id), 300, producer), 'Loaded')


@location_bp.post('/zones/<int:zone_id>/locations/create')
@auth_required()
def create_zone_location(zone_id):
    payload = request.get_json(silent=True) or {}
    name = (payload.get('locationName') or '').strip()
    if not name:
        return fail(1411, 'Enter a location name.')
    db = get_db()
    zone_row = db.fetchone('select id from campus_zones where id = ? and is_deleted = 0', (zone_id,))
    if not zone_row:
        return fail(1403, 'The zone was not found.')
    exists = db.fetchone('select id from locations where zone_id = ? and location_name = ? and is_deleted = 0', (zone_id, name))
    if exists:
        return fail(1412, 'This zone already has a location with that name.')
    now = now_string()
    cur = db.execute('insert into locations (zone_id, location_name, create_time, update_time, is_deleted) values (?, ?, ?, ?, 0)', (zone_id, name, now, now))
    db.commit()
    _clear_location_cache()
    append_log(g.current_user, 'Add Location', f'/api/locations/zones/{zone_id}/locations', 'POST', 10)
    row = db.fetchone('select * from locations where id = ? and is_deleted = 0', (cur.lastrowid,))
    return success(serialize_location(row), 'Saved')


@location_bp.put('/update/<int:location_id>')
@auth_required()
def update_location(location_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    row = db.fetchone('select * from locations where id = ? and is_deleted = 0', (location_id,))
    if not row:
        return fail(1413, 'The location was not found.')
    name = (payload.get('locationName') or row.get('location_name') or '').strip()
    if not name:
        return fail(1411, 'Enter a location name.')
    duplicate = db.fetchone('select id from locations where zone_id = ? and location_name = ? and id <> ? and is_deleted = 0', (row['zone_id'], name, location_id))
    if duplicate:
        return fail(1412, 'This zone already has a location with that name.')
    db.execute('update locations set location_name = ?, update_time = ?, is_deleted = 0 where id = ?', (name, now_string(), location_id))
    db.commit()
    _clear_location_cache()
    append_log(g.current_user, 'Edit Location', f'/api/locations/{location_id}', 'PUT', 10)
    result = db.fetchone('select * from locations where id = ? and is_deleted = 0', (location_id,))
    return success(serialize_location(result), 'Updated')


@location_bp.delete('/delete/<int:location_id>')
@auth_required()
def delete_location(location_id):
    db = get_db()
    row = db.fetchone('select id from locations where id = ? and is_deleted = 0', (location_id,))
    if not row:
        return fail(1413, 'The location was not found.')
    if db.fetchone('select id from plants where location_id = ? and is_deleted = 0 limit 1', (location_id,)):
        return fail(1414, 'This location is still used by plants and cannot be deleted.')
    db.execute('update locations set is_deleted = 1, update_time = ? where id = ?', (now_string(), location_id))
    db.commit()
    _clear_location_cache()
    append_log(g.current_user, 'Delete Location', f'/api/locations/{location_id}', 'DELETE', 10)
    return success({}, 'Deleted')


@location_bp.get('/hierarchy')
@auth_required()
def list_hierarchy():
    def producer():
        db = get_db()
        zones = db.fetchall('select * from campus_zones where is_deleted = 0 order by id asc')
        result = []
        for zone in zones:
            locations = db.fetchall('select * from locations where zone_id = ? and is_deleted = 0 order by id asc', (zone['id'],))
            result.append({'id': zone['id'], 'zoneName': zone.get('zone_name', ''), 'locations': [serialize_location(row) for row in locations]})
        return result

    return success(redis_remember_json('locations', ('hierarchy',), 300, producer), 'Loaded')


