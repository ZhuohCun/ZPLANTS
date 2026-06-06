from datetime import datetime

from flask import Blueprint, g, request

from server.auth import auth_required
from server.common import FEATURE_TO_MODULE_ID, REMINDER_STATUS_TEXT
from server.db import get_db
from server.logger import append_log
from server.blueprints.care_reminder_engine import can_process_early, capture_record_snapshot, compute_reminder_due_time, parse_time
from server.responses import fail, now_string, success
from server.utils import format_display_datetime, paginate

care_reminders_bp = Blueprint('care_reminders', __name__)


@care_reminders_bp.get('/reminders/list')
@auth_required()
def list_reminders():
    db = get_db()
    status = request.args.get('status')
    zone_id = request.args.get('zoneId')
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 5)
    rows = db.fetchall(
        '''select cr.id,
                  p.location_id,
                  cr.plant_id,
                  cr.process_state,
                  cr.is_valid,
                  cr.create_time,
                  rec.create_time as process_time,
                  rec.remark as process_remark,
                  rec.snapshot_species_name,
                  rec.snapshot_zone_name,
                  rec.snapshot_location_name,
                  rec.snapshot_method_name,
                  rec.snapshot_cycle_days,
                  l.location_name,
                  z.zone_name,
                  z.id as zone_id,
                  s.species_name,
                  cr.care_rule_id,
                  rec.operator_real_name as processed_by_name,
                  rule.cycle_days,
                  cm.method_name as care_method_name
           from care_reminders cr
           left join plants p on cr.plant_id = p.id
           left join locations l on p.location_id = l.id
           left join campus_zones z on l.zone_id = z.id
           left join species s on p.species_id = s.id
           left join care_rules rule on cr.care_rule_id = rule.id
           left join care_methods cm on rule.care_method_id = cm.id
           left join (
               select x.reminder_id,
                      x.create_time,
                      x.remark,
                      x.snapshot_species_name,
                      x.snapshot_zone_name,
                      x.snapshot_location_name,
                      x.snapshot_method_name,
                      x.snapshot_cycle_days,
                      u.real_name as operator_real_name
               from care_records x
               inner join (
                   select reminder_id, max(id) as max_id
                   from care_records
                   group by reminder_id
               ) latest_record on latest_record.max_id = x.id
               left join users u on x.operator_user_id = u.id
           ) rec on rec.reminder_id = cr.id
           order by cr.create_time desc, cr.id desc'''
    )
    grouped = []
    by_location = {}
    for row in rows:
        process_state = int(row.get('process_state') or 0)
        if status not in [None, '', 'all'] and process_state != int(status):
            continue
        active_zone_id = row.get('zone_id') or 0
        if zone_id not in [None, '', 'all'] and int(active_zone_id or 0) != int(zone_id):
            continue

        if process_state == 1:
            if int(row.get('is_valid') or 0) != 1:
                continue
            species_name = row.get('species_name', '')
            zone_name = row.get('zone_name', '')
            location_name = row.get('location_name', '')
            reminder_type = row.get('care_method_name', '')
            rule_cycle_days = row.get('cycle_days') or ''
        else:
            species_name = row.get('snapshot_species_name') or row.get('species_name', '')
            zone_name = row.get('snapshot_zone_name') or row.get('zone_name', '')
            location_name = row.get('snapshot_location_name') or row.get('location_name', '')
            reminder_type = row.get('snapshot_method_name') or row.get('care_method_name', '')
            rule_cycle_days = row.get('snapshot_cycle_days') or row.get('cycle_days') or ''

        group_key = row.get('location_id') or f'{zone_name} - {location_name}' or 0
        if group_key not in by_location:
            group = {
                'locationId': group_key if isinstance(group_key, int) else 0,
                'zoneName': zone_name,
                'locationName': location_name,
                'items': [],
                'latestCreateTime': row.get('create_time', ''),
            }
            by_location[group_key] = group
            grouped.append(group)
        display_name = ' · '.join([item for item in [species_name, zone_name, location_name] if item])
        item = {
            'id': row['id'],
            'displayName': display_name,
            'speciesName': species_name,
            'reminderType': reminder_type,
            'status': REMINDER_STATUS_TEXT.get(process_state, ''),
            'statusCode': process_state,
            'createTime': row.get('create_time', ''),
            'processTime': format_display_datetime(row.get('process_time', '')),
            'processRemark': row.get('process_remark', ''),
            'processedByName': row.get('processed_by_name', ''),
            'ruleName': reminder_type,
            'ruleCycleDays': rule_cycle_days,
        }
        by_location[group_key]['items'].append(item)
    grouped.sort(key=lambda item: item.get('latestCreateTime', ''), reverse=True)
    for group in grouped:
        group['items'].sort(key=lambda item: item.get('createTime', ''), reverse=True)
        group.pop('latestCreateTime', None)
    return success(paginate(grouped, page_num, page_size), 'Loaded')


@care_reminders_bp.post('/reminders/process/<int:reminder_id>')
@auth_required()
def process_reminder(reminder_id):
    payload = request.get_json(silent=True) or {}
    process_result = int(payload.get('processResult') or 2)
    if process_result not in [2, 3]:
        return fail(1201, 'The selected status is not valid.')
    db = get_db()
    row = db.fetchone('select * from care_reminders where id = ?', (reminder_id,))
    if not row:
        return fail(1202, 'The care reminder was not found.')
    if int(row.get('process_state') or 0) != 1:
        return fail(1203, 'This reminder has already been completed. Refresh and try again.')
    if int(row.get('is_valid') or 0) != 1:
        return fail(1205, 'This reminder is no longer current. Refresh and try again.')
    if process_result == 2:
        timing_row = db.fetchone(
            """select cr.plant_id,
                      cr.care_rule_id,
                      rule.cycle_days,
                      rule.create_time as rule_create_time,
                      rule.update_time as rule_update_time,
                      latest.last_record_time
               from care_reminders cr
               left join care_rules rule on cr.care_rule_id = rule.id
               left join (
                   select base.plant_id, base.care_rule_id, max(r.create_time) as last_record_time
                   from care_records r
                   left join care_reminders base on r.reminder_id = base.id
                   where r.operation_status in (1, 2)
                   group by base.plant_id, base.care_rule_id
               ) latest on latest.plant_id = cr.plant_id and latest.care_rule_id = cr.care_rule_id
               where cr.id = ?""",
            (reminder_id,),
        )
        if not timing_row or int(timing_row.get('cycle_days') or 0) <= 0:
            return fail(1205, 'This reminder is no longer current. Refresh and try again.')
        rule_effective_time = parse_time(timing_row.get('rule_update_time') or timing_row.get('rule_create_time'))
        if not rule_effective_time:
            return fail(1205, 'This reminder is no longer current. Refresh and try again.')
        due_time = compute_reminder_due_time(
            parse_time(timing_row.get('last_record_time')),
            timing_row.get('cycle_days'),
            rule_effective_time,
        )
        if not can_process_early(datetime.now(), due_time):
            return fail(1206, 'This reminder can only be completed within 12 hours before the expected care time.')
    process_time = now_string()
    snapshot = capture_record_snapshot(db, reminder_id)
    db.execute(
        'update care_reminders set process_state = ?, is_valid = 1 where id = ?',
        (process_result, reminder_id),
    )
    db.execute(
        'insert into care_records (reminder_id, operator_user_id, operation_status, remark, snapshot_species_name, snapshot_zone_name, snapshot_location_name, snapshot_method_name, snapshot_cycle_days, create_time) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row['id'], g.current_user['id'], 1 if process_result == 2 else 2, payload.get('processRemark', ''), snapshot['snapshot_species_name'], snapshot['snapshot_zone_name'], snapshot['snapshot_location_name'], snapshot['snapshot_method_name'], snapshot['snapshot_cycle_days'], process_time),
    )
    db.commit()
    append_log(g.current_user, 'Complete Care Reminder', f'/api/care/reminders/{reminder_id}/process', 'POST', FEATURE_TO_MODULE_ID['care'])
    return success({}, 'Completed')
