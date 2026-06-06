from __future__ import annotations

import sys
import os
import uuid
import hmac
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, jsonify, request
from PIL import Image
MODEL_SERVICE_HOST = '0.0.0.0'
MODEL_SERVICE_PORT = 5100
MODEL_SERVICE_THREADS = 64
MODEL_SERVICE_BACKLOG = 65535
MODEL_MAX_CONTENT_LENGTH = 12 * 1024 * 1024
MODEL_MAX_IMAGE_PIXELS = 80_000_000
MODEL_INFERENCE_MAX_WORKERS = 1
MODEL_SERVICE_INTERNAL_TOKEN = os.environ.get('MODEL_SERVICE_INTERNAL_TOKEN', 'change-this-internal-token-before-public-deployment')

CURRENT_FILE = Path(__file__).resolve()
MODEL_ROOT = CURRENT_FILE.parents[1]
MODEL_ROOT_STR = str(MODEL_ROOT)
if MODEL_ROOT_STR not in sys.path:
    sys.path.insert(0, MODEL_ROOT_STR)

Image.MAX_IMAGE_PIXELS = MODEL_MAX_IMAGE_PIXELS


inference_executor = ThreadPoolExecutor(max_workers=MODEL_INFERENCE_MAX_WORKERS, thread_name_prefix='model-infer')


def _check_internal_token():
    expected = str(MODEL_SERVICE_INTERNAL_TOKEN or '').strip()
    if not expected:
        return None
    received = request.headers.get('X-Internal-Token', '')
    if not hmac.compare_digest(received, expected):
        return jsonify({'code': 403, 'msg': 'Forbidden.', 'data': None}), 403
    return None


def _run_prediction(temp_path: Path, topk: int):
    from application_layer.flask_bridge import get_predictor

    predictor = get_predictor()
    return predictor.predict(str(temp_path), topk=topk)


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MODEL_MAX_CONTENT_LENGTH


@app.after_request
def allow_all_origins(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Internal-Token'
    return response


def _save_temp_image(image_file):
    temp_dir = Path(__file__).resolve().parent / 'predict_io'
    temp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(image_file.filename or 'upload.jpg').suffix or '.jpg'
    temp_path = temp_dir / f'{uuid.uuid4().hex}{suffix}'
    image_file.save(temp_path)
    return temp_path


def _validate_temp_image(temp_path: Path):
    try:
        with Image.open(temp_path) as image:
            image.load()
            if image.width * image.height > MODEL_MAX_IMAGE_PIXELS:
                return jsonify({'code': 413, 'msg': 'Image pixels exceed the model service safety limit.', 'data': None}), 413
    except Image.DecompressionBombError:
        return jsonify({'code': 413, 'msg': 'Image pixels exceed the model service safety limit.', 'data': None}), 413
    except Image.DecompressionBombWarning:
        return jsonify({'code': 413, 'msg': 'Image pixels exceed the model service safety limit.', 'data': None}), 413
    except Exception:
        return jsonify({'code': 400, 'msg': 'Only image files are supported.', 'data': None}), 400
    return None


@app.get('/internal/health')
def health():
    return jsonify({'code': 0, 'msg': 'success', 'data': {'status': 'ok'}})


@app.post('/internal/predict')
def predict():
    token_error = _check_internal_token()
    if token_error is not None:
        return token_error
    if 'image' not in request.files:
        return jsonify({'code': 400, 'msg': 'Missing image file.', 'data': None}), 400
    image_file = request.files['image']
    temp_path = _save_temp_image(image_file)
    topk = max(1, min(int(request.form.get('topk', 3)), 10))
    validation_error = _validate_temp_image(temp_path)
    if validation_error is not None:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return validation_error
    try:
        future = inference_executor.submit(_run_prediction, temp_path, topk)
        result = future.result()
        return jsonify({'code': 0, 'msg': 'success', 'data': result})
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == '__main__':
    try:
        from waitress import serve
    except Exception as exc:
        raise RuntimeError('waitress is not installed. Install it in the deployment environment before starting the model service.') from exc
    serve(app, host=MODEL_SERVICE_HOST, port=MODEL_SERVICE_PORT, threads=MODEL_SERVICE_THREADS, backlog=MODEL_SERVICE_BACKLOG)
