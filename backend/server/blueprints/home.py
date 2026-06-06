
from flask import Blueprint, g

from server.auth import auth_required, has_feature_permission
from server.db import get_db
from server.responses import success
from server.blueprints.model_client import model_health_check, ModelServiceError
from server.cache import redis_cache_status

home_bp = Blueprint('home', __name__)
health_bp = Blueprint('health', __name__)


@health_bp.get('')
def health_root():
    return success({'status': 'ok'}, 'Service is running')


@health_bp.get('/redis')
def health_redis():
    return success(redis_cache_status(), 'Redis cache check completed')


@health_bp.get('/model')
def health_model():
    try:
        payload = model_health_check()
    except ModelServiceError as exc:
        payload = {'reachable': False, 'statusCode': exc.status, 'payload': {'code': exc.code, 'msg': exc.message}, 'url': ''}
    return success(payload, 'Model service check completed')


@home_bp.get('/overview')
@home_bp.get('/summary')
@auth_required()
def overview():
    db = get_db()
    user = g.current_user

    species_count = db.scalar('select count(*) as count from species where is_deleted = 0', default=0)
    plant_count = db.scalar('select count(*) as count from plants where is_deleted = 0', default=0)
    feedback_count = db.scalar('select count(*) as count from feedbacks', default=0)

    can_view_records = has_feature_permission(user, 'recognition', 'view_records')
    if user.get('role') != 'admin':
        recognition_count = db.scalar('select count(*) as count from recognitions where user_id = ?', (user['id'],), 0) if can_view_records else 0
        recent_recognitions = db.fetchall(
            '''select r.id, s.species_name as speciesName, r.image_url as imageUrl, r.create_time as createTime
               from recognitions r
               left join species s on r.species_id = s.id and s.is_deleted = 0
               where r.user_id = ?
               order by r.id desc
               limit 5''',
            (user['id'],),
        ) if can_view_records else []
    else:
        recognition_count = db.scalar('select count(*) as count from recognitions', default=0) if can_view_records else 0
        recent_recognitions = db.fetchall(
            '''select r.id, s.species_name as speciesName, r.image_url as imageUrl, r.create_time as createTime
               from recognitions r
               left join species s on r.species_id = s.id and s.is_deleted = 0
               where 1 = 1
               order by r.id desc
               limit 5'''
        ) if can_view_records else []

    if has_feature_permission(user, 'care', 'view'):
        reminder_rows = db.fetchall(
            '''select cr.id,
                      z.zone_name as zoneName,
                      l.location_name as locationName,
                      s.species_name as speciesName,
                      cm.method_name as reminderType,
                      cr.create_time as createTime,
                      cr.plant_id as plantId,
                      p.location_id as locationId,
                      cr.care_rule_id as careRuleId,
                      rule.cycle_days as ruleCycleDays,
                      cr.process_state as statusCode
               from care_reminders cr
               left join plants p on cr.plant_id = p.id
               left join locations l on p.location_id = l.id
               left join campus_zones z on l.zone_id = z.id
               left join species s on p.species_id = s.id
               left join care_rules rule on cr.care_rule_id = rule.id
               left join care_methods cm on rule.care_method_id = cm.id
               where cr.process_state = 1
                 and cr.is_valid = 1
               order by cr.create_time desc, cr.id desc'''
        )
        pending_reminders = []
        for row in reminder_rows:
            item = dict(row)
            pending_reminders.append(item)
        pending_reminder_count = len(pending_reminders)
    else:
        pending_reminder_count = 0
        pending_reminders = []

    return success(
        {
            'speciesCount': species_count,
            'plantCount': plant_count,
            'recognitionCount': recognition_count,
            'pendingReminderCount': pending_reminder_count,
            'feedbackCount': feedback_count,
            'recentRecognitions': recent_recognitions,
            'pendingReminders': pending_reminders,
        },
        'Loaded',
    )
