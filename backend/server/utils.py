from __future__ import annotations

import base64
import random
import tempfile
from datetime import datetime
from pathlib import Path

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename

from server.common import get_species_distribution_text
from server.db import get_db
from server.errors import ApiError
from server.responses import to_display_datetime
from server.blueprints.model_client import predict_image
from server.security import ALLOWED_IMAGE_EXTENSIONS
from server.cache import redis_remember_json


def paginate(items, page_num=1, page_size=5):
    page_num = max(int(page_num or 1), 1)
    page_size = max(int(page_size or 10), 1)
    start = (page_num - 1) * page_size
    end = start + page_size
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total else 1
    return {'list': items[start:end], 'pageNum': page_num, 'pageSize': page_size, 'total': total, 'totalPages': total_pages}


def paginate_query(list_sql, count_sql, params=None, page_num=1, page_size=5):
    db = get_db()
    page_num = max(int(page_num or 1), 1)
    page_size = max(int(page_size or 10), 1)
    offset = (page_num - 1) * page_size
    query_params = tuple(params or ())
    total = int(db.scalar(count_sql, query_params, 0) or 0)
    rows = db.fetchall(f'{list_sql} limit ? offset ?', query_params + (page_size, offset))
    total_pages = (total + page_size - 1) // page_size if total else 1
    return {'list': rows, 'pageNum': page_num, 'pageSize': page_size, 'total': total, 'totalPages': total_pages}


def format_display_datetime(value):
    return to_display_datetime(value)


def fetch_species_image(species_id):
    row = get_db().fetchone('select image_url from species_images where species_id = ? and is_deleted = 0 order by id desc limit 1', (species_id,))
    return row.get('image_url', '') if row else ''


def replace_species_image(species_id, image_url):
    db = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = db.fetchall('select id, is_deleted from species_images where species_id = ? order by is_deleted asc, id asc', (species_id,))
    if rows:
        target_row = rows[0]
        db.execute('update species_images set image_url = ?, update_time = ?, is_deleted = 0 where id = ?', (image_url, now, target_row['id']))
        for extra in rows[1:]:
            if int(extra.get('is_deleted') or 0) == 0:
                db.execute('update species_images set is_deleted = 1, update_time = ? where id = ?', (now, extra['id']))
        return
    if image_url:
        db.execute('insert into species_images (species_id, image_url, create_time, update_time, is_deleted) values (?, ?, ?, ?, 0)', (species_id, image_url, now, now))


def build_image_url(filename):
    if not filename:
        return ''
    text = str(filename).replace('\\', '/')
    return text if text.startswith('/') else '/' + text.lstrip('/')


def _register_heif_support():
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        return True
    except Exception:
        return False


def _normalize_target_ext(original_name):
    ext = Path(original_name or '').suffix.lower()
    if ext == '.png':
        return '.png'
    if ext in {'.jpg', '.jpeg'}:
        return '.jpg'
    if ext in {'.webp', '.bmp', '.heic', '.heif', '.hif'}:
        return '.jpg'
    raise ApiError(1104, 'Choose a clear plant photo.', 400)


def _make_target_path(upload_folder, sub_folder, original_name):
    source_ext = Path(original_name or '').suffix.lower() or '.jpg'
    if source_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ApiError(1104, 'Choose a clear plant photo.', 400)
    ext = _normalize_target_ext(original_name)
    safe_stem = secure_filename(Path(original_name or 'upload').stem) or 'upload'
    folder = Path(upload_folder) / sub_folder / datetime.now().strftime('%Y%m%d')
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%H%M%S%f')}_{random.randint(100, 999)}_{safe_stem}{ext}"
    return folder / filename


def _open_and_validate_image(source_path: Path, source_ext: str):
    ext = str(source_ext or '').lower()
    if ext in {'.heic', '.heif', '.hif'} and not _register_heif_support():
        raise ApiError(1104, 'The picture could not be read. Choose another clear picture.', 400)
    try:
        image = Image.open(source_path)
        image.load()
        max_pixels = int(current_app.config.get('UPLOAD_IMAGE_MAX_PIXELS', 80_000_000) or 80_000_000)
        if image.width * image.height > max_pixels:
            raise ApiError(1106, 'The picture is too large. Choose a clear picture with a moderate size.', 413)
        return image
    except ApiError:
        raise
    except Image.DecompressionBombError as exc:
        raise ApiError(1106, 'The picture is too large. Choose a clear picture with a moderate size.', 413) from exc
    except Image.DecompressionBombWarning as exc:
        raise ApiError(1106, 'The picture is too large. Choose a clear picture with a moderate size.', 413) from exc
    except Exception as exc:
        raise ApiError(1104, 'Only image files can be uploaded.', 400) from exc


def _write_standard_image(source_path, target_path, source_ext):
    with _open_and_validate_image(Path(source_path), source_ext) as image:
        if target_path.suffix.lower() == '.png':
            image.save(target_path, format='PNG')
        else:
            image.convert('RGB').save(target_path, format='JPEG', quality=92, optimize=True)


def save_upload(file_storage, upload_folder, sub_folder='recognitions'):
    original_name = file_storage.filename or 'upload.jpg'
    source_ext = Path(original_name).suffix.lower() or '.jpg'
    target = _make_target_path(upload_folder, sub_folder, original_name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=source_ext or '.tmp') as temp_file:
        file_storage.save(temp_file.name)
        temp_path = Path(temp_file.name)
    try:
        _write_standard_image(temp_path, target, source_ext)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
    relative = '/' + str(target.relative_to(Path(upload_folder).parent)).replace('\\', '/')
    return relative, str(target)


def save_base64_upload(image_base64, upload_folder, sub_folder='recognitions'):
    try:
        payload = image_base64.split(',', 1)[1] if ',' in image_base64 else image_base64
        binary = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ApiError(1104, 'The picture could not be read. Choose another clear picture.', 400) from exc
    target = _make_target_path(upload_folder, sub_folder, 'capture.jpg')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
        temp_file.write(binary)
        temp_path = Path(temp_file.name)
    try:
        _write_standard_image(temp_path, target, '.jpg')
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
    relative = '/' + str(target.relative_to(Path(upload_folder).parent)).replace('\\', '/')
    return relative, str(target)


def fetch_species_for_model():
    return redis_remember_json(
        'model_species',
        ('active-species',),
        300,
        lambda: get_db().fetchall('select id, species_name, scientific_name from species where is_deleted = 0 order by id asc'),
    )


def fetch_species_detail(species_id):
    db = get_db()
    row = db.fetchone('select * from species where id = ? and is_deleted = 0', (species_id,))
    if not row:
        return None

    location_rows = db.fetchall(
        '''select z.id as zone_id, z.zone_name, l.id as location_id, l.location_name
           from plants p
           left join locations l on p.location_id = l.id and l.is_deleted = 0
           left join campus_zones z on l.zone_id = z.id and z.is_deleted = 0
           where p.species_id = ? and p.is_deleted = 0
           group by z.id, z.zone_name, l.id, l.location_name
           order by z.zone_name asc, l.location_name asc''',
        (species_id,),
    )
    plant_rows = db.fetchall(
        '''select p.id, z.zone_name, l.location_name
           from plants p
           left join locations l on p.location_id = l.id and l.is_deleted = 0
           left join campus_zones z on l.zone_id = z.id and z.is_deleted = 0
           where p.species_id = ? and p.is_deleted = 0
           order by z.zone_name asc, l.location_name asc, p.id asc''',
        (species_id,),
    )
    rule_rows = db.fetchall(
        '''select cr.id, cr.cycle_days, cm.id as care_method_id, cm.method_name
           from care_rules cr
           inner join care_methods cm on cr.care_method_id = cm.id and cm.is_deleted = 0
           where cr.species_id = ? and cr.is_deleted = 0
           order by cr.id asc''',
        (species_id,),
    )
    plants = []
    for item in plant_rows:
        display_name = f"{row.get('species_name', '')} {item.get('zone_name', '')} - {item.get('location_name', '')}".strip()
        plants.append({'id': item['id'], 'displayName': display_name, 'zoneName': item.get('zone_name', ''), 'locationName': item.get('location_name', '')})
    care_rules = [{'id': r['id'], 'careMethodId': r.get('care_method_id'), 'methodName': r.get('method_name', ''), 'cycleDays': r.get('cycle_days') or ''} for r in rule_rows]
    return {
        'id': row['id'],
        'speciesName': row.get('species_name', ''),
        'scientificName': row.get('scientific_name', ''),
        'carePoints': row.get('care_points', ''),
        'lightRequirement': row.get('light_requirement', ''),
        'distribution': get_species_distribution_text(species_id),
        'locations': location_rows,
        'plants': plants,
        'instances': plants,
        'plantCount': len(plant_rows),
        'imageUrl': fetch_species_image(species_id),
        'careRules': care_rules,
        'care_rules': care_rules,
    }


def filter_species_detail_by_permissions(detail, can_view_distribution=True, can_view_plants=True):
    if not detail:
        return detail
    filtered = dict(detail)
    if not can_view_distribution:
        filtered['distribution'] = ''
        filtered['locations'] = []
    if not can_view_plants:
        filtered['plants'] = []
        filtered['instances'] = []
    return filtered


def filter_plant_detail_by_permissions(detail, can_view_distribution=True):
    if not detail:
        return detail
    filtered = dict(detail)
    if not can_view_distribution:
        filtered['distribution'] = ''
        filtered['locations'] = []
    return filtered


def filter_plant_list_by_permissions(items, can_view_distribution=True):
    filtered_items = []
    for item in items or []:
        row = dict(item)
        if not can_view_distribution:
            row['distribution'] = ''
        filtered_items.append(row)
    return filtered_items


def choose_recognition(species_rows, filename='', image_path=None, topk=3):
    predictions = predict_image(image_path, filename=filename, topk=topk)
    if not species_rows:
        raise ApiError(1105, 'No plant species are available for recognition yet.', 400)
    id_lookup = {row['id']: row for row in species_rows}
    name_lookup = {}
    for row in species_rows:
        species_name = str(row.get('species_name') or '').strip().lower()
        scientific_name = str(row.get('scientific_name') or '').strip().lower()
        if species_name:
            name_lookup[species_name] = row
        if scientific_name:
            name_lookup[scientific_name] = row
    selected = None
    mapped = []
    for item in predictions:
        species_row = None
        species_id = item.get('speciesId')
        if species_id in id_lookup:
            species_row = id_lookup[species_id]
        if species_row is None:
            species_row = name_lookup.get(str(item.get('label') or '').strip().lower())
        if species_row is None:
            continue
        if selected is None:
            selected = species_row
        mapped.append({'speciesId': species_row['id'], 'confidence': float(item.get('confidence') or 0), 'clusterId': item.get('clusterId')})
    if selected is None:
        selected = species_rows[0]
        mapped = [{'speciesId': selected['id'], 'confidence': 1.0, 'clusterId': 'cluster-01'}]
    return selected, mapped
