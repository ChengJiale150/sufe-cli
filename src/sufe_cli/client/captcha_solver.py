from dataclasses import dataclass

import cv2
import numpy as np

MIN_TEMPLATE_PIXELS = 100
MIN_MATCH_SCORE = 0.9
HOLE_WHITE_THRESHOLD = 245


@dataclass(frozen=True)
class CaptchaMatch:
    center_x: float
    center_y: float
    top_left_x: float
    top_left_y: float
    score: float
    template_width: int
    template_height: int


def _alpha_mask(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] < 4:
        msg = "滑块模板必须包含 alpha 通道"
        raise ValueError(msg)
    return (image[:, :, 3] > 0).astype(np.float32)


def _hole_mask(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        gray = image
        alpha = np.full(image.shape, 255, dtype=np.uint8)
    elif image.ndim == 3 and image.shape[2] >= 3:
        gray = image[:, :, :3].min(axis=2)
        alpha = image[:, :, 3] if image.shape[2] >= 4 else np.full(image.shape[:2], 255, dtype=np.uint8)
    else:
        msg = "验证码背景图格式无效"
        raise ValueError(msg)

    return ((gray >= HOLE_WHITE_THRESHOLD) & (alpha > 0)).astype(np.float32)


def _crop_nonzero(mask: np.ndarray) -> tuple[np.ndarray, int, int]:
    ys, xs = np.where(mask > 0)
    if len(xs) < MIN_TEMPLATE_PIXELS:
        msg = "滑块模板有效像素过少"
        raise ValueError(msg)

    x0 = int(xs.min())
    x1 = int(xs.max())
    y0 = int(ys.min())
    y1 = int(ys.max())
    return mask[y0 : y1 + 1, x0 : x1 + 1], x0, y0


def _subpixel_peak(response: np.ndarray, x: int, y: int) -> tuple[float, float]:
    def vertex_offset(previous: float, current: float, next_: float) -> float:
        denominator = previous - (2.0 * current) + next_
        if abs(denominator) < 1e-12:
            return 0.0
        offset = 0.5 * (previous - next_) / denominator
        return float(np.clip(offset, -0.5, 0.5))

    dx = 0.0
    dy = 0.0
    if 0 < x < response.shape[1] - 1:
        dx = vertex_offset(float(response[y, x - 1]), float(response[y, x]), float(response[y, x + 1]))
    if 0 < y < response.shape[0] - 1:
        dy = vertex_offset(float(response[y - 1, x]), float(response[y, x]), float(response[y + 1, x]))
    return dx, dy


def match_gap_from_images(background: np.ndarray, slider_template: np.ndarray) -> CaptchaMatch:
    """Match the slider alpha silhouette against the white gap in the background."""
    template_mask, visible_offset_x, visible_offset_y = _crop_nonzero(_alpha_mask(slider_template))
    background_mask = _hole_mask(background)

    if background_mask.shape[0] < template_mask.shape[0] or background_mask.shape[1] < template_mask.shape[1]:
        msg = "验证码背景图小于滑块模板"
        raise ValueError(msg)

    response = cv2.matchTemplate(background_mask, template_mask, cv2.TM_CCORR_NORMED)
    _, max_value, _, max_location = cv2.minMaxLoc(response)
    score = float(max_value)
    if score < MIN_MATCH_SCORE:
        msg = f"验证码缺口匹配置信度过低: {score:.4f}"
        raise ValueError(msg)

    peak_x, peak_y = max_location
    dx, dy = _subpixel_peak(response, peak_x, peak_y)
    top_left_x = float(peak_x + dx - visible_offset_x)
    top_left_y = float(peak_y + dy - visible_offset_y)

    return CaptchaMatch(
        center_x=top_left_x + slider_template.shape[1] / 2,
        center_y=top_left_y + slider_template.shape[0] / 2,
        top_left_x=top_left_x,
        top_left_y=top_left_y,
        score=score,
        template_width=int(slider_template.shape[1]),
        template_height=int(slider_template.shape[0]),
    )


def find_gap_from_images(background: np.ndarray, slider_template: np.ndarray | None) -> float:
    if slider_template is None:
        msg = "缺少滑块模板图，无法精确匹配验证码缺口"
        raise ValueError(msg)
    return match_gap_from_images(background, slider_template).center_x


def get_tracks(distance: float, *, steps: int = 36) -> list[float]:
    """Create a float drag track whose sum is exactly the requested distance."""
    if distance <= 0:
        return []

    actual_steps = max(8, int(min(steps, max(8, distance / 2))))
    times = np.linspace(0.0, 1.0, actual_steps + 1)
    positions = distance * (3 * times**2 - 2 * times**3)
    offsets = np.diff(positions).astype(float).tolist()
    offsets[-1] += float(distance - sum(offsets))
    return offsets
