from pathlib import Path

import cv2
import numpy as np
import pytest

from sufe_cli.client.auth.captcha_solver import find_gap_from_images, get_tracks, match_gap_from_images

DATA_DIR = Path(__file__).parent / "data"


def _read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert image is not None
    return image


@pytest.mark.parametrize(
    ("index", "expected_x", "expected_y"),
    [
        (1, 318.0, 180.0),
        (2, 342.0, 115.0),
        (3, 212.0, 178.0),
        (4, 156.0, 110.0),
        (5, 304.0, 269.0),
    ],
)
def test_match_gap_from_real_images(index: int, expected_x: float, expected_y: float) -> None:
    background = _read_image(DATA_DIR / f"bg{index}.png")
    slider = _read_image(DATA_DIR / f"mask{index}.png")

    match = match_gap_from_images(background, slider)

    assert match.center_x == pytest.approx(expected_x, abs=0.2)
    assert match.center_y == pytest.approx(expected_y, abs=0.2)
    assert match.score >= 0.98
    assert find_gap_from_images(background, slider) == pytest.approx(match.center_x, abs=1e-9)


def test_find_gap_requires_slider_template() -> None:
    background = _read_image(DATA_DIR / "bg1.png")

    with pytest.raises(ValueError, match="缺少滑块模板图"):
        find_gap_from_images(background, None)


def test_get_tracks_preserves_float_distance() -> None:
    distance = 123.4567
    tracks = get_tracks(distance)

    assert tracks
    assert sum(tracks) == pytest.approx(distance, abs=1e-9)
    assert all(offset > 0 for offset in tracks)
