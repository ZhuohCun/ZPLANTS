
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision.models import EfficientNet_V2_S_Weights, efficientnet_v2_s

BACKBONE_NAME = 'efficientnet_v2_s'
ARCHITECTURE_NAME = 'efficientnet_v2_s_cbam'
ATTENTION_NAME = 'cbam'
DEFAULT_DROPOUT = 0.20
DEFAULT_IMAGE_SIZE = 384
DEFAULT_RESIZE_SIZE = 384


class ChannelAttention(nn.Module):

    def __init__(self, channels: int, reduction: int = 16) -> None:
        super().__init__()
        hidden = max(int(channels // reduction), 32)
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc1 = nn.Conv2d(channels, hidden, kernel_size=1, bias=True)
        self.relu = nn.ReLU(inplace=True)
        self.fc2 = nn.Conv2d(hidden, channels, kernel_size=1, bias=True)
        nn.init.zeros_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def _path(self, pooled: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.relu(self.fc1(pooled)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        attention = 0.5 + torch.sigmoid(self._path(self.avg_pool(x)) + self._path(self.max_pool(x)))
        return x * attention


class SpatialAttention(nn.Module):

    def __init__(self, kernel_size: int = 7) -> None:
        super().__init__()
        padding = kernel_size // 2
        self.conv = nn.Conv2d(2, 1, kernel_size=kernel_size, padding=padding, bias=True)
        nn.init.zeros_(self.conv.weight)
        nn.init.zeros_(self.conv.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_map = torch.mean(x, dim=1, keepdim=True)
        max_map, _ = torch.max(x, dim=1, keepdim=True)
        attention = 0.5 + torch.sigmoid(self.conv(torch.cat([avg_map, max_map], dim=1)))
        return x * attention


class CBAMRefiner(nn.Module):

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.channel_attention = ChannelAttention(channels)
        self.spatial_attention = SpatialAttention(kernel_size=7)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x


class EfficientNetFeatureExtractor(nn.Module):

    def __init__(self, pretrained: bool = True) -> None:
        super().__init__()
        weights = EfficientNet_V2_S_Weights.DEFAULT if pretrained else None
        backbone = efficientnet_v2_s(weights=weights)
        self.features = backbone.features
        self.pool = backbone.avgpool
        self.out_features = backbone.classifier[1].in_features
        self.cbam = CBAMRefiner(self.out_features)
        self.backbone_name = BACKBONE_NAME
        self.architecture_name = ARCHITECTURE_NAME
        self.attention_name = ATTENTION_NAME

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.cbam(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return x


class EfficientNetV2SClassifier(nn.Module):

    def __init__(self, num_classes: int, pretrained: bool = True, dropout: float = DEFAULT_DROPOUT) -> None:
        super().__init__()
        weights = EfficientNet_V2_S_Weights.DEFAULT if pretrained else None
        backbone = efficientnet_v2_s(weights=weights)
        in_features = int(backbone.classifier[1].in_features)
        backbone.classifier[0] = nn.Dropout(p=float(dropout), inplace=True)
        backbone.classifier[1] = nn.Linear(in_features, int(num_classes))
        self.features = backbone.features
        self.cbam = CBAMRefiner(in_features)
        self.pool = backbone.avgpool
        self.classifier = backbone.classifier
        self.channels = in_features
        self.backbone_name = BACKBONE_NAME
        self.architecture_name = ARCHITECTURE_NAME
        self.attention_name = ATTENTION_NAME

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.cbam(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.forward_features(x)
        return self.classifier(x)
