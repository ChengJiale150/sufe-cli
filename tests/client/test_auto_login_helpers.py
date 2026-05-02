import pytest

from sufe_cli.client.auth.auto_login import _captcha_target_details


def test_captcha_target_details_corrects_move_slider_range_ratio() -> None:
    target = _captcha_target_details(
        271.03653704494167,
        {"x": 832, "y": 290, "width": 240, "height": 132.171875},
        (483, 266),
        {"x": 832, "y": 435.171875, "width": 40, "height": 40},
        {"x": 832, "y": 294.46875, "width": 49, "height": 49},
    )

    assert target.gap_page_x == pytest.approx(966.6765401465549)
    assert target.move_center_x == pytest.approx(856.5)
    assert target.raw_move_delta == pytest.approx(110.17654014655488)
    assert target.move_per_slider == pytest.approx((240 - 49) / (240 - 40))
    assert target.corrected_drag_delta == pytest.approx(115.3681048655025)
    assert target.target_x == pytest.approx(967.3681048655025)
