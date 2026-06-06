
from flask import Blueprint, request

from server.auth import auth_required
from server.responses import success, to_display_datetime
from server.utils import paginate_query

operation_logs_bp = Blueprint('operation_logs', __name__)


@operation_logs_bp.get('/list')
@auth_required()
def list_logs():
    page_num = request.args.get('pageNum', 1)
    page_size = request.args.get('pageSize', 10)
    keyword = (request.args.get('keyword') or '').strip()
    base_sql = """select ol.id, ol.user_id as operator_user_id, u.username, u.real_name, m.module_name, ol.operation_name, ol.request_url, ol.request_method, ol.ip, ol.ip_location, ol.create_time
                  from operation_logs ol
                  left join users u on ol.user_id = u.id
                  left join modules m on ol.module_id = m.id"""
    count_sql = """select count(*) as total
                   from operation_logs ol
                   left join users u on ol.user_id = u.id
                   left join modules m on ol.module_id = m.id"""
    params = []
    if keyword:
        like_value = f'%{keyword}%'
        where_clause = """ where coalesce(u.username, '') like ?
                              or coalesce(u.real_name, '') like ?
                              or coalesce(m.module_name, '') like ?
                              or coalesce(ol.operation_name, '') like ?
                              or coalesce(ol.ip, '') like ?
                              or coalesce(ol.ip_location, '') like ?
                              or coalesce(ol.request_url, '') like ?"""
        base_sql += where_clause
        count_sql += where_clause
        params.extend([like_value] * 7)
    rows = paginate_query(
        base_sql + ' order by ol.id desc',
        count_sql,
        tuple(params), page_num, page_size,
    )
    result = []
    for row in rows['list']:
        result.append({
            'id': row['id'],
            'operatorId': row.get('operator_user_id'),
            'username': row.get('username') or 'Visitor',
            'realName': row.get('real_name') or row.get('username') or 'Visitor',
            'operationModule': row.get('module_name', ''),
            'operationName': row.get('operation_name', ''),
            'requestUrl': row.get('request_url', ''),
            'requestMethod': row.get('request_method', ''),
            'ip': row.get('ip', ''),
            'ipLocation': row.get('ip_location', ''),
            'createTime': to_display_datetime(row.get('create_time', '')),
        })
    rows['list'] = result
    return success(rows, 'Search completed')
