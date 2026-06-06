
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    from model_layer.predictor import EfficientNetPredictor
except Exception:
    EfficientNetPredictor = None

MODEL_SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODEL_ARTIFACT_DIR = MODEL_SERVICE_ROOT / 'artifacts'
MODEL_CHECKPOINT_FILE = 'deploy_model.pt'
CLUSTER_ARTIFACT_FILE = 'cluster_artifacts.pt'
CLUSTER_CENTROIDS_FILE = 'cluster_centroids.pt'


def _norm_text(value):
    return (value or '').strip().lower()


def resolve_model_artifact_dir() -> Path:
    return MODEL_ARTIFACT_DIR.resolve()


def resolve_model_checkpoint_path(model_dir: Path) -> Path:
    return model_dir / MODEL_CHECKPOINT_FILE


def resolve_cluster_artifact_path(model_dir: Path) -> Path:
    return model_dir / CLUSTER_ARTIFACT_FILE


def resolve_cluster_centroids_path(model_dir: Path) -> Path:
    return model_dir / CLUSTER_CENTROIDS_FILE


@lru_cache(maxsize=1)
def get_predictor():
    if EfficientNetPredictor is None:
        raise RuntimeError('The model predictor is unavailable. Please verify that the model dependencies are installed correctly.')
    model_dir = resolve_model_artifact_dir()
    checkpoint_path = resolve_model_checkpoint_path(model_dir)
    cluster_artifact_path = resolve_cluster_artifact_path(model_dir)
    cluster_centroids_path = resolve_cluster_centroids_path(model_dir)
    missing = []
    if not checkpoint_path.exists():
        missing.append(str(checkpoint_path))
    if not cluster_centroids_path.exists():
        missing.append(str(cluster_centroids_path))
    if missing:
        raise RuntimeError(
            'Recognition requires deploy_model.pt and cluster_centroids.pt under model_service/artifacts. '
            'cluster_artifacts.pt is optional. Missing: ' + '; '.join(missing)
        )
    device = 'cuda' if torch_cuda_available() else 'cpu'
    return EfficientNetPredictor(
        str(checkpoint_path),
        str(cluster_artifact_path) if cluster_artifact_path.exists() else None,
        str(cluster_centroids_path),
        device=device,
    )


def torch_cuda_available():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def normalize_cluster_id(cluster_id, fallback_index):
    text_value = str(cluster_id or '').strip()
    if text_value:
        return text_value
    safe_index = max(1, int(fallback_index or 1))
    return f'cluster-{safe_index:02d}'


def map_prediction_to_plant(plants, predicted_label):
    predicted_label_norm = _norm_text(predicted_label)
    for plant in plants:
        if _norm_text(plant['plant_name']) == predicted_label_norm:
            return plant
    for plant in plants:
        if predicted_label_norm in _norm_text(plant['plant_name']):
            return plant
    for plant in plants:
        scientific_name = _norm_text(plant.get('scientific_name'))
        if scientific_name and predicted_label_norm == scientific_name:
            return plant
    return plants[0] if plants else None


def choose_recognition(plants, filename='', image_path=None, topk=3):
    if not plants:
        return None, []
    predictor = get_predictor()
    predictions = predictor.predict(image_path=image_path, topk=topk)
    topk_results = []
    selected_target = None
    for index, item in enumerate(predictions, start=1):
        plant = map_prediction_to_plant(plants, item['label'])
        if plant is None:
            continue
        confidence = max(0.0, min(float(item.get('confidence', 0.0)), 1.0))
        cluster_id = item.get('clusterId') or normalize_cluster_id(None, index)
        result = {
            'id': plant['id'],
            'speciesId': plant['id'],
            'speciesName': plant['plant_name'],
            'scientificName': plant.get('scientific_name', ''),
            'confidence': confidence,
            'clusterId': cluster_id,
            'rank': index,
        }
        if selected_target is None:
            selected_target = result
        topk_results.append(result)
    if selected_target is None:
        fallback = plants[0]
        selected_target = {
            'id': fallback['id'],
            'speciesId': fallback['id'],
            'speciesName': fallback['plant_name'],
            'scientificName': fallback.get('scientific_name', ''),
            'confidence': 0.0,
            'clusterId': normalize_cluster_id(None, 1),
            'rank': 1,
        }
        topk_results = [selected_target]
    return selected_target, topk_results
