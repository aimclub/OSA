import albumentations as A
import cv2
from albumentations.pytorch import ToTensorV2
from torchvision import transforms


def get_transformer(face_policy: str, patch_size: int, net_normalizer: transforms.Normalize):
    # Transformers and traindb
    if face_policy == 'scale':
        # The loader crops the face isotropically then scales to a square of size patch_size_load
        loading_transformations = [
            A.PadIfNeeded(min_height=patch_size, min_width=patch_size,
                          border_mode=cv2.BORDER_CONSTANT, value=0, always_apply=True),
            A.Resize(height=patch_size, width=patch_size, always_apply=True),
        ]
    elif face_policy == 'tight':
        # The loader crops the face tightly without any scaling
        loading_transformations = [
            A.LongestMaxSize(max_size=patch_size, always_apply=True),
            A.PadIfNeeded(min_height=patch_size, min_width=patch_size,
                          border_mode=cv2.BORDER_CONSTANT, value=0, always_apply=True),
        ]
    else:
        raise ValueError('Unknown value for face_policy: {}'.format(face_policy))

    # Common final transformations
    final_transformations = [A.Normalize(mean=net_normalizer.mean, std=net_normalizer.std), ToTensorV2()]
    transf = A.Compose(loading_transformations + final_transformations)

    return transf


def get_extended_bbox(box, extend_coef=3.8):
    xmin, ymin, xmax, ymax = list(map(int, box))
    w = xmax - xmin
    h = ymax - ymin
    p_w = int(w // extend_coef)
    p_h = int(h // extend_coef)

    ymin, ymax, xmin, xmax = max(ymin - p_h, 0), ymax + p_h, max(xmin - p_w, 0), xmax + p_w
    return xmin, ymin, xmax, ymax


def crop_face(image, box):
    xmin, ymin, xmax, ymax = get_extended_bbox(box)
    crop = image[ymin:ymax, xmin:xmax]
    return crop
