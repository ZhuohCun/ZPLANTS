from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple

from server.db import get_db
from server.responses import now_string

REMINDER_ADVANCE_SECONDS = 2 * 24 * 60 * 60
PROCESS_EARLY_SECONDS = 12 * 60 * 60
SCHEDULER_LOCK_NAME = 'care_reminder_scheduler_lock'


def parse_time(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            continue
    return None


def compute_due_time(last_record_time: datetime, cycle_days: int) -> datetime:
    return last_record_time + timedelta(days=int(cycle_days or 0))


def compute_reminder_due_time(last_record_time: Optional[datetime], cycle_days: int, rule_effective_time: datetime) -> datetime:
    base_time = last_record_time or rule_effective_time
    return compute_due_time(base_time, cycle_days)


def _changed_after_reminder(row, reminder_created_time: Optional[datetime]) -> bool:
    if not reminder_created_time:
        return False
    for field_name in [
        'plant_update_time',
        'species_update_time',
        'location_update_time',
        'zone_update_time',
        'rule_update_time',
        'method_update_time',
    ]:
        changed_time = parse_time(row.get(field_name))
        if changed_time and changed_time > reminder_created_time:
            return True
    return False


def reminder_status(now: datetime, due_time: datetime) -> Tuple[str, float]:
    remaining_seconds = (due_time - now).total_seconds()
    if due_time.date() > now.date() and remaining_seconds <= REMINDER_ADVANCE_SECONDS:
        return 'Due Soon', remaining_seconds
    if due_time.date() == now.date():
        return 'Due Today', remaining_seconds
    return 'Overdue', remaining_seconds


def _english_day_text(day_count: int) -> str:
    return '1 day' if int(day_count or 0) == 1 else f'{int(day_count or 0)} days'


def reminder_due_text(now: datetime, due_time: datetime) -> str:
    remaining_seconds = (due_time - now).total_seconds()
    if remaining_seconds > 0:
        if remaining_seconds <= 86400:
            return 'Care is needed tomorrow' if due_time.date() > now.date() else 'Care is needed today'
        remaining_days = max(1, int((remaining_seconds + 86399) // 86400))
        return f'Care is due in {_english_day_text(remaining_days)}'
    if due_time.date() == now.date():
        return 'Care is needed today'
    overdue_days = max(1, int((abs(remaining_seconds) + 86399) // 86400))
    return f'Overdue by {_english_day_text(overdue_days)}'


def can_process_early(now: datetime, due_time: datetime) -> bool:
    remaining_seconds = (due_time - now).total_seconds()
    return remaining_seconds <= PROCESS_EARLY_SECONDS


def _fetch_rule_instances(db, species_id):
    return db.fetchall(
        """select p.id as plant_id,
                  l.id as location_id,
                  l.location_name,
                  z.zone_name
           from plants p
           inner join locations l on p.location_id = l.id and l.is_deleted = 0
           inner join campus_zones z on l.zone_id = z.id and z.is_deleted = 0
           where p.species_id = ? and p.is_deleted = 0""",
        (species_id,),
    )


def _latest_record(db, plant_id, rule_id):
    return db.fetchone(
        """select r.create_time
           from care_records r
           left join care_reminders cr on r.reminder_id = cr.id
           where cr.plant_id = ? and cr.care_rule_id = ? and r.operation_status in (1, 2)
           order by r.create_time desc, r.id desc
           limit 1""",
        (plant_id, rule_id),
    )


def _pending_reminder(db, plant_id, rule_id):
    return db.fetchone(
        """select id
           from care_reminders
           where plant_id = ? and care_rule_id = ? and process_state = 1 and is_valid = 1
           order by id desc
           limit 1""",
        (plant_id, rule_id),
    )


def _try_acquire_scheduler_lock(db) -> bool:
    row = db.fetchone('select GET_LOCK(?, 0) as acquired', (SCHEDULER_LOCK_NAME,))
    return bool(int((row or {}).get('acquired') or 0))


def _release_scheduler_lock(db) -> None:
    try:
        db.fetchone('select RELEASE_LOCK(?) as released', (SCHEDULER_LOCK_NAME,))
    except Exception:
        pass


def capture_record_snapshot(db, reminder_id: int) -> dict:
    row = db.fetchone(
        """select ps.species_name,
                  z.zone_name,
                  l.location_name,
                  cm.method_name,
                  rule.cycle_days
           from care_reminders cr
           left join plants p on cr.plant_id = p.id
           left join locations l on p.location_id = l.id
           left join campus_zones z on l.zone_id = z.id
           left join species ps on p.species_id = ps.id
           left join care_rules rule on cr.care_rule_id = rule.id and rule.species_id = p.species_id
           left join care_methods cm on rule.care_method_id = cm.id
           where cr.id = ?""",
        (reminder_id,),
    ) or {}
    return {
        'snapshot_species_name': row.get('species_name', '') or '',
        'snapshot_zone_name': row.get('zone_name', '') or '',
        'snapshot_location_name': row.get('location_name', '') or '',
        'snapshot_method_name': row.get('method_name', '') or '',
        'snapshot_cycle_days': int(row.get('cycle_days') or 0),
    }


def clear_invalid_care_reminders(trigger='manual', now: Optional[datetime] = None, db=None, commit: bool = True):
    db = db or get_db()
    now = now or datetime.now()
    rows = db.fetchall(
        """select cr.id,
                  cr.plant_id,
                  cr.care_rule_id,
                  cr.process_state,
                  cr.is_valid,
                  cr.create_time,
                  p.id as live_plant_id,
                  p.species_id as live_species_id,
                  p.location_id,
                  p.update_time as plant_update_time,
                  p.is_deleted as plant_is_deleted,
                  ps.id as live_species_row_id,
                  ps.update_time as species_update_time,
                  ps.is_deleted as species_is_deleted,
                  l.id as live_location_id,
                  l.update_time as location_update_time,
                  l.is_deleted as location_is_deleted,
                  z.id as live_zone_id,
                  z.update_time as zone_update_time,
                  z.is_deleted as zone_is_deleted,
                  rule.id as live_rule_id,
                  rule.cycle_days,
                  rule.create_time as rule_create_time,
                  rule.update_time as rule_update_time,
                  rule.is_deleted as rule_is_deleted,
                  cm.id as live_method_id,
                  cm.update_time as method_update_time,
                  cm.is_deleted as method_is_deleted
           from care_reminders cr
           left join plants p on cr.plant_id = p.id
           left join species ps on p.species_id = ps.id
           left join locations l on p.location_id = l.id
           left join campus_zones z on l.zone_id = z.id
           left join care_rules rule on cr.care_rule_id = rule.id and rule.species_id = p.species_id
           left join care_methods cm on rule.care_method_id = cm.id
           where cr.process_state = 1"""
    )
    updated_count = 0
    for row in rows:
        new_valid = 1
        reminder_created_time = parse_time(row.get('create_time'))
        if not row.get('live_plant_id') or not row.get('live_species_row_id') or not row.get('live_location_id') or not row.get('live_zone_id') or not row.get('live_rule_id') or not row.get('live_method_id'):
            new_valid = 0
        elif int(row.get('plant_is_deleted') or 0) == 1 or int(row.get('species_is_deleted') or 0) == 1 or int(row.get('location_is_deleted') or 0) == 1 or int(row.get('zone_is_deleted') or 0) == 1 or int(row.get('rule_is_deleted') or 0) == 1 or int(row.get('method_is_deleted') or 0) == 1:
            new_valid = 0
        elif int(row.get('cycle_days') or 0) <= 0:
            new_valid = 0
        elif _changed_after_reminder(row, reminder_created_time):
            new_valid = 0
        if int(row.get('is_valid') or 0) != int(new_valid):
            db.execute('update care_reminders set is_valid = ? where id = ?', (new_valid, row['id']))
            updated_count += 1
    if commit and updated_count:
        db.commit()
    if updated_count:
        print(f'[Care Reminder Engine][{trigger}] Cleared {updated_count} invalid pending reminder(s).')


def generate_new_care_reminders(trigger='manual', now: Optional[datetime] = None, db=None, commit: bool = True):
    db = db or get_db()
    now = now or datetime.now()
    created_count = 0
    rules = db.fetchall(
        """select cr.id as care_rule_id,
                  cr.cycle_days,
                  cr.create_time as rule_create_time,
                  cr.update_time as rule_update_time,
                  cm.id as care_method_id,
                  cm.method_name,
                  sp.id as species_id,
                  sp.species_name
           from care_rules cr
           inner join care_methods cm on cr.care_method_id = cm.id and cm.is_deleted = 0
           inner join species sp on cr.species_id = sp.id and sp.is_deleted = 0
           where cr.cycle_days > 0 and cr.is_deleted = 0"""
    )
    for rule in rules:
        for item in _fetch_rule_instances(db, rule['species_id']):
            last_record = _latest_record(db, item['plant_id'], rule['care_rule_id'])
            last_time = parse_time(last_record['create_time']) if last_record else None
            due_time = compute_reminder_due_time(
                last_time,
                rule['cycle_days'],
                parse_time(rule.get('rule_update_time') or rule.get('rule_create_time')),
            )
            _state_text, remaining_seconds = reminder_status(now, due_time)
            if remaining_seconds > REMINDER_ADVANCE_SECONDS:
                continue
            if _pending_reminder(db, item['plant_id'], rule['care_rule_id']):
                continue
            db.execute(
                'insert into care_reminders (plant_id, care_rule_id, process_state, is_valid, create_time) values (?, ?, ?, ?, ?)',
                (item['plant_id'], rule['care_rule_id'], 1, 1, now_string()),
            )
            created_count += 1
    if commit and created_count:
        db.commit()
    print(f'[Care Reminder Engine][{trigger}] New reminder generation completed. Created {created_count} reminder(s).')


def run_care_reminder_engine(trigger='manual', now: Optional[datetime] = None, db=None):
    db = db or get_db()
    if db.supports_named_locks and not _try_acquire_scheduler_lock(db):
        print(f'[Care Reminder Engine][{trigger}] Another node already holds the scheduler lock. This pass was skipped.')
        return
    now = now or datetime.now()
    try:
        clear_invalid_care_reminders(f'{trigger}-clear-invalid', now=now, db=db, commit=False)
        generate_new_care_reminders(f'{trigger}-generate-new', now=now, db=db, commit=False)
        db.commit()
        print(f'[Care Reminder Engine][{trigger}] Engine pass completed.')
    finally:
        if db.supports_named_locks:
            _release_scheduler_lock(db)


def reconcile_pending_care_reminders(trigger='manual', now: Optional[datetime] = None, db=None, commit: bool = True):
    clear_invalid_care_reminders(trigger=trigger, now=now, db=db, commit=commit)


def ensure_due_care_reminders(trigger='manual', now: Optional[datetime] = None, db=None):
    run_care_reminder_engine(trigger=trigger, now=now, db=db)
