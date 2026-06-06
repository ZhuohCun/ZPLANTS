

from __future__ import annotations

from PIL import Image
from torchvision import transforms
from torchvision.transforms import InterpolationMode

Image.MAX_IMAGE_PIXELS = None

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

DEFAULT_CROP_SIZE = 384
DEFAULT_RESIZE_SIZE = 384


def load_cropped_pil(image_path: str, bbox=None) -> Image.Image:
    image = Image.open(image_path).convert('RGB')
    if bbox is not None:
        xmin, ymin, xmax, ymax = [int(v) for v in bbox]
        xmin = max(0, xmin)
        ymin = max(0, ymin)
        xmax = min(image.width, xmax)
        ymax = min(image.height, ymax)
        if xmax > xmin and ymax > ymin:
            image = image.crop((xmin, ymin, xmax, ymax))
    return image


def build_train_transform(image_size: int = DEFAULT_CROP_SIZE, mean=None, std=None):
    mean = mean or IMAGENET_MEAN
    std = std or IMAGENET_STD
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(
                image_size,
                scale=(0.80, 1.0),
                ratio=(0.75, 1.3333),
                interpolation=InterpolationMode.BILINEAR,
            ),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=8, interpolation=InterpolationMode.BILINEAR),
            transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.10, hue=0.02),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
            transforms.RandomErasing(p=0.15, scale=(0.02, 0.08), ratio=(0.3, 3.3), value='random'),
        ]
    )


def build_eval_transform(image_size: int = DEFAULT_CROP_SIZE, resize_size: int = DEFAULT_RESIZE_SIZE, mean=None, std=None):
    mean = mean or IMAGENET_MEAN
    std = std or IMAGENET_STD
    return transforms.Compose(
        [
            transforms.Resize(resize_size, interpolation=InterpolationMode.BILINEAR),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )


def pil_to_tensor(image: Image.Image, image_size: int = DEFAULT_CROP_SIZE, resize_size: int = DEFAULT_RESIZE_SIZE, mean=None, std=None):
    transform = build_eval_transform(image_size=image_size, resize_size=resize_size, mean=mean, std=std)
    return transform(image)
