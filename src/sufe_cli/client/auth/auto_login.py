import base64
import binascii
import random
from dataclasses import dataclass

import cv2
import numpy as np
from playwright.sync_api import FloatRect, Locator, Page, sync_playwright

from .captcha_solver import CaptchaMatch, get_tracks, match_gap_from_images

LOGIN_URL = "https://login.sufe.edu.cn/login/"
LOGIN_DOMAIN = "login.sufe.edu.cn"
PORTAL_URL = "https://portal.sufe.edu.cn/main.html"
SWITCH_SELECTOR = "#qrcode-box .qrcode-close"
USERNAME_SELECTOR = "input[placeholder*='学号'], input[placeholder*='工号'], input#username, [role='textbox']"
PASSWORD_SELECTOR = "input[type='password'], input#password"
LOGIN_BTN_SELECTOR = "button:has-text('登 录'), .login-btn, #login-btn"
CAPTCHA_TEXT = "请完成安全验证"
CAPTCHA_REFRESH_SELECTOR = ".slider-refresh, .icon-refresh, .refresh-btn, .refresh"
CAPTCHA_CLOSE_SELECTOR = ".slider-close, .icon-close"
SLIDER_IMG_SELECTOR = ".slider-img-bg"
SLIDER_MOVE_SELECTOR = ".slider-img-move"
SLIDER_SELECTOR = "#slider-move-box, .slider-move-box"
SUBPIXEL_RELEASE_TOLERANCE = 1e-3
RAW_DATA_URL_SOURCE = "raw-data-url"
SCREENSHOT_FALLBACK_SOURCE = "locator-screenshot"


@dataclass(frozen=True)
class _CaptchaImage:
    image: np.ndarray
    source: str
    natural_size: tuple[int, int]


@dataclass(frozen=True)
class _CaptchaTarget:
    target_x: float
    scale_x: float
    scale_y: float
    gap_page_x: float
    slider_start_x: float | None
    move_center_x: float | None
    raw_move_delta: float | None
    move_per_slider: float
    corrected_drag_delta: float | None


def _decode_data_url_image(data_url: str) -> np.ndarray:
    """解码 img[src=data:image/png;base64,...] 为 OpenCV 图像数组。"""
    if not data_url.startswith("data:image/") or "," not in data_url:
        msg = "验证码图片不是 data URL"
        raise ValueError(msg)

    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        msg = "验证码 data URL 不是 base64 编码"
        raise ValueError(msg)

    try:
        raw = base64.b64decode(encoded, validate=True)
    except binascii.Error as e:
        msg = "验证码 data URL base64 解码失败"
        raise ValueError(msg) from e

    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        msg = "验证码图片解码失败"
        raise ValueError(msg)

    return image


def _decode_png_bytes(raw: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        msg = "验证码截图解码失败"
        raise ValueError(msg)
    return image


def _locator_natural_size(locator: Locator) -> tuple[int, int] | None:
    """读取 img 元素的 naturalWidth/naturalHeight。"""
    try:
        natural = locator.evaluate(
            """img => ({
                width: img.naturalWidth || 0,
                height: img.naturalHeight || 0
            })"""
        )
    except Exception:
        return None

    if not isinstance(natural, dict):
        return None

    width = natural.get("width")
    height = natural.get("height")
    if not isinstance(width, int | float) or not isinstance(height, int | float):
        return None

    width_i = int(width)
    height_i = int(height)
    if width_i <= 0 or height_i <= 0:
        return None

    return width_i, height_i


def _image_size(image: np.ndarray) -> tuple[int, int]:
    """返回 OpenCV 图像的 (width, height)。"""
    height, width = image.shape[:2]
    return width, height


def _locator_image_src(locator: Locator) -> str:
    try:
        src = locator.evaluate("img => img.currentSrc || img.src || ''")
    except Exception:
        return ""
    return src if isinstance(src, str) else ""


def _read_locator_image(locator: Locator) -> _CaptchaImage:
    """优先读取 img 原始 data URL，失败后退回内存元素截图。"""
    if not locator.is_visible():
        msg = "验证码图片元素不可见"
        raise ValueError(msg)

    src = _locator_image_src(locator)
    if isinstance(src, str) and src.startswith("data:image/"):
        try:
            image = _decode_data_url_image(src)
            natural_size = _locator_natural_size(locator) or _image_size(image)
            return _CaptchaImage(image=image, source=RAW_DATA_URL_SOURCE, natural_size=natural_size)
        except ValueError:
            pass

    screenshot_image = _decode_png_bytes(locator.screenshot())

    return _CaptchaImage(
        image=screenshot_image,
        source=SCREENSHOT_FALLBACK_SOURCE,
        natural_size=_image_size(screenshot_image),
    )


def _locator_box(locator: Locator) -> FloatRect | None:
    try:
        return locator.bounding_box(timeout=1000)
    except Exception:
        return None


def _captcha_target_details(
    gap_x_relative: float,
    img_box: FloatRect | None,
    image_size: tuple[int, int] | None,
    slider_box: FloatRect | None = None,
    move_box: FloatRect | None = None,
) -> _CaptchaTarget:
    """把验证码原始图像内的缺口坐标转换为滑块应到达的页面 x 坐标。"""
    if img_box is None:
        return _CaptchaTarget(
            target_x=float(gap_x_relative),
            scale_x=1.0,
            scale_y=1.0,
            gap_page_x=float(gap_x_relative),
            slider_start_x=None,
            move_center_x=None,
            raw_move_delta=None,
            move_per_slider=1.0,
            corrected_drag_delta=None,
        )

    scale_x = 1.0
    scale_y = 1.0
    if image_size is not None:
        image_w, image_h = image_size
        scale_x = img_box["width"] / image_w if image_w > 0 else 1.0
        scale_y = img_box["height"] / image_h if image_h > 0 else 1.0

    gap_page_x = float(img_box["x"] + gap_x_relative * scale_x)
    if slider_box is None or move_box is None:
        return _CaptchaTarget(
            target_x=gap_page_x,
            scale_x=float(scale_x),
            scale_y=float(scale_y),
            gap_page_x=gap_page_x,
            slider_start_x=None,
            move_center_x=None,
            raw_move_delta=None,
            move_per_slider=1.0,
            corrected_drag_delta=None,
        )

    slider_start_x = float(slider_box["x"] + slider_box["width"] / 2)
    move_center_x = float(move_box["x"] + move_box["width"] / 2)
    raw_move_delta = gap_page_x - move_center_x
    move_range = float(img_box["width"] - move_box["width"])
    slider_range = float(img_box["width"] - slider_box["width"])
    move_per_slider = move_range / slider_range if move_range > 0 and slider_range > 0 else 1.0
    corrected_drag_delta = raw_move_delta / move_per_slider if move_per_slider > 0 else raw_move_delta
    return _CaptchaTarget(
        target_x=slider_start_x + corrected_drag_delta,
        scale_x=float(scale_x),
        scale_y=float(scale_y),
        gap_page_x=gap_page_x,
        slider_start_x=slider_start_x,
        move_center_x=move_center_x,
        raw_move_delta=raw_move_delta,
        move_per_slider=move_per_slider,
        corrected_drag_delta=corrected_drag_delta,
    )


def _human_like_drag(page, slider: Locator, target_x: float) -> None:
    """模拟人类拖动滑块到目标页面 x 坐标（支持 sub-pixel 精度）。"""
    box = slider.bounding_box()
    if box is None:
        return
    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2
    distance = target_x - start_x

    if distance <= 0:
        return

    tracks = get_tracks(distance)

    page.mouse.move(start_x, start_y)
    page.mouse.down()

    current_x = start_x
    for offset in tracks:
        current_x += offset
        jitter_y = start_y + random.uniform(-1.5, 1.5)
        page.mouse.move(current_x, jitter_y)
        page.wait_for_timeout(random.randint(10, 30))

    if abs(current_x - target_x) > SUBPIXEL_RELEASE_TOLERANCE:
        page.mouse.move(target_x, start_y + random.uniform(-0.4, 0.4))

    page.mouse.up()


def _wait_for_any(page: Page, *selectors: str, timeout: int = 10000) -> Locator | None:
    """依次尝试多个选择器，等待第一个可见的元素出现。"""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


def _wait_for_login_success(page: Page, *, timeout: int = 3500) -> bool:
    try:
        page.wait_for_function("domain => !window.location.href.includes(domain)", arg=LOGIN_DOMAIN, timeout=timeout)
    except Exception:
        return LOGIN_DOMAIN not in page.url
    return True


def _save_storage_state_with_portal(page, context, storage_state_path: str | None) -> None:
    """登录成功后，确保 portal 页面加载完毕并保存 storage state。

    会等待 portal 页面的 localStorage token 初始化完成，以捕获完整的认证状态。
    """
    if storage_state_path is None:
        return

    try:
        if "portal.sufe.edu.cn" not in page.url:
            page.goto(PORTAL_URL)
        page.wait_for_load_state("networkidle", timeout=15000)
        # 等待 portal 页面的 localStorage token 初始化（最多 10 秒）
        page.wait_for_function(
            "() => localStorage.getItem('token') !== null && localStorage.getItem('token') !== ''",
            timeout=10000,
        )
    except Exception:
        pass  # 即使等待失败也继续保存，至少能捕获 cookies

    context.storage_state(path=storage_state_path)


def _safe_click(locator: Locator, *, timeout: int = 1500) -> bool:
    try:
        if locator.is_visible():
            locator.click(timeout=timeout)
            return True
    except Exception:
        return False
    return False


def _is_visible(page: Page, selector: str) -> bool:
    try:
        return page.locator(selector).first.is_visible()
    except Exception:
        return False


def _wait_for_captcha_image_change(page: Page, previous_src: str, *, timeout: int = 8000) -> bool:
    try:
        page.wait_for_function(
            """([selector, previous]) => {
                const img = document.querySelector(selector);
                const src = img ? (img.currentSrc || img.src || "") : "";
                return Boolean(src) && src !== previous;
            }""",
            arg=[SLIDER_IMG_SELECTOR, previous_src],
            timeout=timeout,
        )
    except Exception:
        return False
    return True


def _wait_for_captcha_ready(page: Page, *, timeout: int = 8000) -> bool:
    try:
        page.wait_for_selector(SLIDER_IMG_SELECTOR, state="visible", timeout=timeout)
        page.wait_for_selector(SLIDER_MOVE_SELECTOR, state="visible", timeout=timeout)
    except Exception:
        return False
    return True


def _refresh_captcha(page: Page, login_btn: Locator, previous_src: str) -> bool:
    refresh_btn = page.locator(CAPTCHA_REFRESH_SELECTOR).first
    if _safe_click(refresh_btn):
        if _wait_for_captcha_image_change(page, previous_src, timeout=3500) or _wait_for_captcha_ready(
            page, timeout=2500
        ):
            return True

    close_btn = page.locator(CAPTCHA_CLOSE_SELECTOR).first
    _safe_click(close_btn)

    try:
        page.wait_for_selector(f"text={CAPTCHA_TEXT}", state="hidden", timeout=2500)
    except Exception:
        pass

    if not _safe_click(login_btn, timeout=3000):
        return _is_visible(page, SLIDER_IMG_SELECTOR) and _is_visible(page, SLIDER_MOVE_SELECTOR)

    try:
        page.wait_for_selector(f"text={CAPTCHA_TEXT}", state="visible", timeout=10000)
    except Exception:
        pass

    if previous_src and _wait_for_captcha_image_change(page, previous_src, timeout=3500):
        return True
    return _wait_for_captcha_ready(page, timeout=5000)


def attempt_login(
    username: str,
    password: str,
    *,
    headless: bool = True,
    max_captcha_retries: int = 3,
    storage_state_path: str | None = None,
) -> tuple[bool, str]:
    """自动完成上财统一认证登录流程。

    Args:
        username: 学号或工号。
        password: 密码。
        headless: 是否以无头模式运行浏览器，默认 True；调试建议设为 False。
        max_captcha_retries: 验证码失败后的最大重试次数，默认 3 次。
        storage_state_path: 登录成功后保存 Playwright storage state 的路径。

    Returns:
        (是否成功, 当前 URL 或错误信息)。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. 访问登录页（使用 load 而非 networkidle，避免轮播图等持续资源导致超时）
            page.goto(LOGIN_URL, wait_until="load", timeout=60000)

            # 2. 切换到账号密码登录
            # 先等待二维码切换按钮出现并点击
            try:
                page.wait_for_selector("#qrcode-box", timeout=15000)
                switch_btn = page.locator(SWITCH_SELECTOR).first
                switch_btn.wait_for(state="visible", timeout=5000)
                switch_btn.click()
                # 等待切换后的账号密码登录标签出现，确认切换成功
                page.wait_for_selector("text=账号密码登录", timeout=5000)
            except Exception:
                # 如果切换按钮不存在，可能默认就是账号密码登录界面
                pass

            # 等待账号密码登录表单渲染完成
            user_input = _wait_for_any(page, USERNAME_SELECTOR, timeout=15000)
            pwd_input = _wait_for_any(page, PASSWORD_SELECTOR, timeout=15000)
            login_btn = _wait_for_any(page, LOGIN_BTN_SELECTOR, timeout=15000)

            if user_input is None or pwd_input is None or login_btn is None:
                return False, "未找到用户名/密码输入框或登录按钮"

            # 3. 填充用户名和密码
            user_input.fill(username)
            pwd_input.fill(password)

            # 4. 点击登录，触发可能的验证码
            login_btn.click()

            # 5. 等待验证码弹窗出现或页面跳转（首轮验证码加载可能需要较长时间）
            try:
                page.wait_for_selector(f"text={CAPTCHA_TEXT}", timeout=30000)
            except Exception:
                # 30 秒内验证码未出现，检查是否已直接跳转成功
                if LOGIN_DOMAIN not in page.url:
                    _save_storage_state_with_portal(page, context, storage_state_path)
                    return True, page.url
                return False, f"登录后未跳转且无验证码，当前页面: {page.url}"

            # 6. 验证码处理循环：识别 → 精确滑动 → 等待跳转；失败后刷新新图再重试
            for attempt in range(1, max_captcha_retries + 1):
                # 等待验证码图片元素加载并可见（首次循环尤其重要）
                try:
                    page.wait_for_selector(SLIDER_IMG_SELECTOR, state="visible", timeout=10000)
                    page.wait_for_selector(SLIDER_MOVE_SELECTOR, state="visible", timeout=5000)
                except Exception:
                    pass  # 即使超时也继续尝试，后续 is_visible() 会处理

                match: CaptchaMatch | None = None
                target_detail: _CaptchaTarget | None = None
                target_x: float | None = None
                bg_data: _CaptchaImage | None = None
                tmpl_data: _CaptchaImage | None = None
                previous_src = ""

                try:
                    bg_img = page.locator(SLIDER_IMG_SELECTOR).first
                    move_img = page.locator(SLIDER_MOVE_SELECTOR).first
                    previous_src = _locator_image_src(bg_img)

                    if not bg_img.is_visible():
                        msg = "验证码背景图元素不可见"
                        raise ValueError(msg)
                    if not move_img.is_visible():
                        msg = "滑块模板图元素不可见"
                        raise ValueError(msg)

                    bg_data = _read_locator_image(bg_img)
                    tmpl_data = _read_locator_image(move_img)

                    match = match_gap_from_images(bg_data.image, tmpl_data.image)

                    # 将截图中的相对坐标转换为页面绝对坐标
                    img_box = _locator_box(bg_img) if bg_img.is_visible() else None
                    move_box = _locator_box(move_img) if move_img.is_visible() else None
                    slider = page.locator(SLIDER_SELECTOR).first
                    slider_box = _locator_box(slider)
                    target_detail = _captcha_target_details(
                        match.center_x,
                        img_box,
                        bg_data.natural_size,
                        slider_box,
                        move_box,
                    )
                    target_x = target_detail.target_x
                except ValueError as e:
                    if attempt < max_captcha_retries:
                        _refresh_captcha(page, login_btn, previous_src)
                        continue
                    return False, f"验证码识别失败: {e}"

                # 找到滑块按钮并拖动
                slider = page.locator(SLIDER_SELECTOR).first
                if not slider.is_visible():
                    if attempt < max_captcha_retries:
                        _refresh_captcha(page, login_btn, previous_src)
                        continue
                    return False, "未找到滑块按钮"
                if target_x is None:
                    if attempt < max_captcha_retries:
                        _refresh_captcha(page, login_btn, previous_src)
                        continue
                    return False, "缺少滑块目标坐标"

                _human_like_drag(page, slider, target_x)

                if _wait_for_login_success(page):
                    _save_storage_state_with_portal(page, context, storage_state_path)
                    return True, page.url

                if attempt < max_captcha_retries:
                    _refresh_captcha(page, login_btn, previous_src)

            return False, f"验证码处理失败，已达最大重试次数 ({max_captcha_retries})"

        except Exception as e:
            return False, f"登录过程异常: {e}"
        finally:
            browser.close()
