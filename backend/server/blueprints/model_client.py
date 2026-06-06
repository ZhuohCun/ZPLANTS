from pathlib import Path
import mimetypes

import requests
from requests import RequestException
from requests.adapters import HTTPAdapter
from flask import current_app

from server.errors import ApiError


class ModelServiceError(ApiError):
    def __init__(self, message, status=503):
        super().__init__(1105, message, status)


_session = None


def _get_session():
    global _session
    if _session is not None:
        return _session
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=int(current_app.config.get('MODEL_HTTP_POOL_CONNECTIONS', 20)),
        pool_maxsize=int(current_app.config.get('MODEL_HTTP_POOL_MAXSIZE', 20)),
        max_retries=0,
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    _session = session
    return _session


def _build_url(path_value):
    base = (current_app.config.get('MODEL_SERVICE_URL') or '').rstrip('/')
    if not base:
        raise ModelServiceError('Model service URL is not configured.')
    path = (path_value or '').strip()
    if not path.startswith('/'):
        path = '/' + path
    return base + path


def _headers():
    token = current_app.config.get('MODEL_SERVICE_INTERNAL_TOKEN', '')
    return {'X-Internal-Token': token} if token else {}


def model_health_check():
    url = _build_url(current_app.config.get('MODEL_HEALTH_PATH'))
    timeout = current_app.config.get('MODEL_API_TIMEOUT')
    verify = current_app.config.get('MODEL_VERIFY_SSL', False)
    try:
        response = _get_session().get(url, timeout=timeout, verify=verify, headers=_headers())
    except RequestException as exc:
        raise ModelServiceError(f'Model service health check failed: {exc}') from exc
    try:
        payload = response.json() if response.content else {}
    except ValueError as exc:
        raise ModelServiceError('Model service returned invalid JSON for health check.') from exc
    return {'reachable': response.ok, 'statusCode': response.status_code, 'payload': payload, 'url': url}


def predict_image(image_path, filename=None, topk=None):
    file_path = Path(image_path)
    if not file_path.exists():
        raise ApiError(1104, f'Recognition image not found:{file_path}', 400)
    url = _build_url(current_app.config.get('MODEL_PREDICT_PATH'))
    timeout = current_app.config.get('MODEL_API_TIMEOUT')
    verify = current_app.config.get('MODEL_VERIFY_SSL', False)
    topk_value = int(topk or current_app.config.get('MODEL_TOPK', 3))
    content_type = mimetypes.guess_type(filename or file_path.name)[0] or 'image/jpeg'
    try:
        with file_path.open('rb') as f:
            files = {'image': (filename or file_path.name, f, content_type)}
            data = {'topk': str(topk_value)}
            response = _get_session().post(url, files=files, data=data, timeout=timeout, verify=verify, headers=_headers())
    except RequestException as exc:
        raise ModelServiceError(f'Model service request failed: {exc}') from exc
    if response.status_code != 200:
        raise ModelServiceError(f'Model service returned status code {response.status_code}.', response.status_code)
    try:
        payload = response.json()
    except ValueError as exc:
        raise ModelServiceError('Model service returned invalid JSON for prediction.') from exc
    if int(payload.get('code', -1)) not in (0, 200):
        raise ModelServiceError(payload.get('msg') or 'Model prediction failed.', response.status_code)
    data = payload.get('data')
    if not isinstance(data, list) or not data:
        raise ModelServiceError('Model service did not return valid prediction items.')
    return data
