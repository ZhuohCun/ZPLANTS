
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from threading import Lock
from typing import Any

import torch

from feature_processing_layer.image_preprocessor import load_cropped_pil, pil_to_tensor
from model_layer.efficientnet_attention import EfficientNetFeatureExtractor, EfficientNetV2SClassifier


class EfficientNetPredictor:

    _engine_lock = Lock()
    _engine_ready = False

    def __init__(
        self,
        checkpoint_path: str,
        cluster_artifacts_path: str | None = None,
        cluster_centroids_path: str | None = None,
        device: str = 'cuda',
    ) -> None:
        requested_device = torch.device(device)
        if requested_device.type == 'cuda' and not torch.cuda.is_available():
            requested_device = torch.device('cpu')
        self.device = requested_device

        self._configure_engine()
        checkpoint = self._torch_load(checkpoint_path)
        if not isinstance(checkpoint, dict):
            raise RuntimeError(f'Invalid checkpoint file: {checkpoint_path}')
        if 'state_dict' not in checkpoint:
            raise RuntimeError(f'deploy_model.pt must contain state_dict: {checkpoint_path}')
        if 'class_to_idx' not in checkpoint or 'idx_to_class' not in checkpoint:
            raise RuntimeError(f'deploy_model.pt must contain class_to_idx and idx_to_class: {checkpoint_path}')

        self.class_to_idx = {str(k): int(v) for k, v in checkpoint['class_to_idx'].items()}
        self.idx_to_class = {int(k): str(v) for k, v in checkpoint['idx_to_class'].items()}
        self.image_size = int(checkpoint.get('image_size', 384))
        self.resize_size = int(checkpoint.get('resize_size', 384))
        self.cluster_count = int(checkpoint.get('cluster_count', len(self.idx_to_class) or 11))
        self.cluster_guidance_strength = float(checkpoint.get('cluster_guidance_strength', 0.35))

        classifier_dropout = float(checkpoint.get('classifier_dropout', 0.20))
        self.model = EfficientNetV2SClassifier(
            num_classes=len(self.class_to_idx),
            pretrained=False,
            dropout=classifier_dropout,
        ).to(self.device)
        if self.device.type == 'cuda':
            self.model = self.model.to(memory_format=torch.channels_last)
        self.model.load_state_dict(checkpoint['state_dict'])
        self.model.eval()

        self.feature_extractor = EfficientNetFeatureExtractor(pretrained=False).to(self.device)
        if self.device.type == 'cuda':
            self.feature_extractor = self.feature_extractor.to(memory_format=torch.channels_last)
        self.feature_extractor.features.load_state_dict(self.model.features.state_dict())
        self.feature_extractor.cbam.load_state_dict(self.model.cbam.state_dict())
        self.feature_extractor.eval()

        self.cluster_centroids = None
        self.cluster_label_priors = None
        self.cluster_artifacts = {}
        self.cluster_guidance_enabled = False
        self.cluster_runtime_mode = 'two-file-neutral-prior'

        if cluster_artifacts_path:
            artifact_path = Path(cluster_artifacts_path).resolve()
            if artifact_path.exists():
                self._load_cluster_artifacts(artifact_path)

        if cluster_centroids_path:
            self._load_cluster_centroids(Path(cluster_centroids_path).resolve())

        self._validate_cluster_runtime()
        self._warmup()

    def _torch_load(self, path):
        try:
            return torch.load(path, map_location=self.device, weights_only=False)
        except TypeError:
            return torch.load(path, map_location=self.device)

    @staticmethod
    def _find_value(obj: Any, keys: tuple[str, ...]) -> Any:
        if isinstance(obj, dict):
            for key in keys:
                if key in obj:
                    return obj[key]
            for value in obj.values():
                found = EfficientNetPredictor._find_value(value, keys)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for value in obj:
                found = EfficientNetPredictor._find_value(value, keys)
                if found is not None:
                    return found
        return None

    def _tensor_from_payload(self, value: Any, name: str) -> torch.Tensor | None:
        if value is None:
            return None
        if torch.is_tensor(value):
            return value.detach().to(device=self.device, dtype=torch.float32)
        try:
            return torch.as_tensor(value, dtype=torch.float32, device=self.device)
        except Exception as exc:
            raise RuntimeError(f'{name} cannot be converted to tensor.') from exc

    def _load_cluster_artifacts(self, artifact_path: Path) -> None:
        payload = self._torch_load(artifact_path)
        if not isinstance(payload, dict):
            return
        self.cluster_artifacts = payload

        priors_value = self._find_value(payload, ('cluster_label_priors', 'class_priors', 'label_priors', 'priors'))
        priors = self._tensor_from_payload(priors_value, 'cluster_label_priors')
        if priors is None or priors.dim() != 2:
            return
        if priors.size(1) != len(self.class_to_idx):
            return
        self.cluster_label_priors = priors / priors.sum(dim=1, keepdim=True).clamp_min(1e-12)
        self.cluster_count = int(payload.get('cluster_count') or self.cluster_label_priors.size(0))
        self.cluster_guidance_strength = float(
            payload.get('cluster_guidance_strength', payload.get('guidance_strength', self.cluster_guidance_strength))
        )
        self.cluster_guidance_enabled = True
        self.cluster_runtime_mode = 'three-file-cluster-prior'

    def _load_cluster_centroids(self, centroids_path: Path) -> None:
        if not centroids_path.exists():
            raise RuntimeError(f'cluster_centroids.pt is missing: {centroids_path}')
        payload = self._torch_load(centroids_path)
        if torch.is_tensor(payload):
            centroids = payload
        elif isinstance(payload, dict):
            centroids = self._find_value(
                payload,
                ('centroids', 'cluster_centroids', 'cluster_centers', 'cluster_centers_', 'centers'),
            )
        else:
            centroids = None
        centroids = self._tensor_from_payload(centroids, 'centroids')
        if centroids is None:
            raise RuntimeError(f'cluster_centroids.pt must contain centroids: {centroids_path}')
        if centroids.dim() != 2:
            raise RuntimeError('centroids must be a 2-D tensor.')
        self.cluster_centroids = centroids
        self.cluster_count = int(centroids.size(0))

    def _validate_cluster_runtime(self) -> None:
        if self.cluster_centroids is None:
            raise RuntimeError('Recognition requires cluster_centroids.pt with valid centroids.')
        if self.cluster_label_priors is None:


            class_count = len(self.class_to_idx)
            rows = int(self.cluster_centroids.size(0))
            self.cluster_label_priors = torch.ones((rows, class_count), dtype=torch.float32, device=self.device)
            self.cluster_label_priors = self.cluster_label_priors / self.cluster_label_priors.sum(dim=1, keepdim=True)
            self.cluster_guidance_enabled = False
            self.cluster_runtime_mode = 'two-file-neutral-prior'
        if self.cluster_label_priors.size(0) != self.cluster_centroids.size(0):
            raise RuntimeError('The number of centroid rows must match the number of prior rows.')
        if self.cluster_label_priors.size(1) != len(self.class_to_idx):
            raise RuntimeError('The prior column count must match the classifier class count.')

    @classmethod
    def _configure_engine(cls) -> None:
        with cls._engine_lock:
            if cls._engine_ready:
                return
            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                try:
                    torch.set_float32_matmul_precision('high')
                except Exception:
                    pass
            cls._engine_ready = True

    def _autocast_context(self):
        if self.device.type == 'cuda':
            return torch.autocast(device_type='cuda', enabled=True)
        return nullcontext()

    def _warmup(self) -> None:
        sample = torch.zeros((1, 3, self.image_size, self.image_size), device=self.device, dtype=torch.float32)
        if self.device.type == 'cuda':
            sample = sample.contiguous(memory_format=torch.channels_last)
        with torch.inference_mode(), self._autocast_context():
            _ = self.model(sample)
            _ = self.feature_extractor(sample)
        if self.device.type == 'cuda':
            torch.cuda.synchronize(self.device)

    def _prepare_tensor(self, image_path: str, bbox=None) -> torch.Tensor:
        image = load_cropped_pil(image_path, bbox=bbox)
        tensor = pil_to_tensor(image, image_size=self.image_size, resize_size=self.resize_size)
        if self.device.type == 'cuda':
            return tensor.unsqueeze(0).to(self.device, non_blocking=True, memory_format=torch.channels_last)
        return tensor.unsqueeze(0).to(self.device)

    def _extract_normalized_features(self, input_tensor: torch.Tensor):
        with torch.inference_mode(), self._autocast_context():
            features = self.feature_extractor(input_tensor)
            return torch.nn.functional.normalize(features, dim=1)

    def _predict_cluster_from_features(self, normalized_features: torch.Tensor):
        distances = torch.cdist(normalized_features.float(), self.cluster_centroids.float())
        cluster_id = torch.argmin(distances, dim=1)
        return int(cluster_id.item())

    def _apply_cluster_guidance(self, probabilities: torch.Tensor, cluster_id: int | None) -> torch.Tensor:
        if cluster_id is None or self.cluster_label_priors is None:
            return probabilities
        if cluster_id < 0 or cluster_id >= self.cluster_label_priors.size(0):
            return probabilities
        cluster_prior = self.cluster_label_priors[cluster_id].unsqueeze(0)
        adjusted = probabilities * torch.pow(cluster_prior, self.cluster_guidance_strength)
        adjusted_sum = adjusted.sum(dim=1, keepdim=True)
        adjusted_sum = torch.where(adjusted_sum > 0, adjusted_sum, torch.ones_like(adjusted_sum))
        return adjusted / adjusted_sum

    def predict(self, image_path: str, topk: int = 3, bbox=None) -> list[dict]:
        input_tensor = self._prepare_tensor(image_path, bbox=bbox)
        normalized_features = self._extract_normalized_features(input_tensor)
        cluster_id = self._predict_cluster_from_features(normalized_features)
        with torch.inference_mode(), self._autocast_context():
            logits = self.model(input_tensor)
            probabilities = torch.softmax(logits.float(), dim=1)
        refined_probabilities = self._apply_cluster_guidance(probabilities, cluster_id)
        values, indices = torch.topk(refined_probabilities, k=min(int(topk), refined_probabilities.size(1)), dim=1)
        normalized_cluster_id = f'cluster-{int(cluster_id) + 1:02d}'

        results = []
        for score, index in zip(values[0].tolist(), indices[0].tolist()):
            results.append({
                'label': self.idx_to_class[int(index)],
                'confidence': float(score),
                'clusterId': normalized_cluster_id,
            })
        return results
