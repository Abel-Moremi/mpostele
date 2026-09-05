from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin


class CaptureError(RuntimeError):
    """Raised when the capture flow cannot complete a requested action
    (e.g. a login was requested but no login form could be found, or no
    submit button could be located)."""


class LoginVerificationError(CaptureError):
    """Raised when a login was submitted but its success could not be
    confirmed within the allotted time (no URL change, the password field
    is still visible, or an error message was detected on the page)."""


# Candidate selectors used to locate login form fields and controls.
# Kept as module-level constants so both the fill logic and the platform
# detection step (`_detect_page_context`) agree on what "a login form" means.
EMAIL_SELECTORS: tuple[str, ...] = (
    "input[type='email']",
    "input[name='email']",
    "input[name='username']",
    "input[name='login']",
    "input[autocomplete='username']",
)

PASSWORD_SELECTORS: tuple[str, ...] = (
    "input[type='password']",
    "input[name='password']",
    "input[autocomplete='current-password']",
)

LOGIN_BUTTON_SELECTORS: tuple[str, ...] = (
    "button:has-text('Log in')",
    "button:has-text('Login')",
    "button:has-text('Sign in')",
    "input[type='submit']",
    "button[type='submit']",
    "button[type='button']",
)

# Selectors for the *entry point* into a login form on a landing/marketing
# page, as opposed to LOGIN_BUTTON_SELECTORS above (the submit control inside
# an already-open form). Clicking one of these may open a modal or navigate
# to a dedicated /login page.
LOGIN_ENTRY_SELECTORS: tuple[str, ...] = (
    "a:has-text('Log in')",
    "a:has-text('Login')",
    "a:has-text('Sign in')",
    "button:has-text('Log in')",
    "button:has-text('Login')",
    "button:has-text('Sign in')",
    "a[href*='login' i]",
    "a[href*='signin' i]",
    "a[href*='sign-in' i]",
)

# Heuristic selectors matching common cookie/consent banners. Case-insensitive
# attribute matching (the trailing `i`) is supported by Chromium, which is the
# only engine this pipeline drives.
DEFAULT_HIDE_SELECTORS: tuple[str, ...] = (
    "[id*='cookie' i]",
    "[class*='cookie' i]",
    "[id*='consent' i]",
    "[class*='consent' i]",
)

# Heuristic selectors used to locate elements that *might* hold a login error
# message. Note that generic containers like `[role='alert']` and `.error`
# are also used by frameworks for unrelated purposes -- e.g. Vue/Nuxt inserts
# an accessibility "route announcer" with `role="alert"` on every navigation
# that simply echoes the page title for screen readers. So a match here is
# only treated as a real failure if its text also looks like an error
# message (see LOGIN_ERROR_TEXT_PATTERN below), not just because the
# selector matched.
LOGIN_ERROR_SELECTORS: tuple[str, ...] = (
    "[role='alert']",
    ".error",
    ".error-message",
    ".alert-danger",
)

# Keywords that indicate an element's text is actually describing a login
# failure, as opposed to incidental page content (titles, announcements,
# unrelated status messages) that happens to match a generic error selector.
LOGIN_ERROR_TEXT_PATTERN = re.compile(
    r"invalid|incorrect|failed|failure|denied|wrong|unrecognized|"
    r"doesn.t match|does not match|try again|unable to (sign|log)",
    re.IGNORECASE,
)


@dataclass
class PageContext:
    """A snapshot of what the capture step learned about the page before
    acting on it, i.e. "understanding the platform" before recording."""

    title: str
    url: str
    has_login_form: bool
    email_selector: str | None
    password_selector: str | None


@dataclass
class CaptureResult:
    screenshot_path: Path
    duration: float
    word_count: int
    page_title: str
    login_verified: bool


def estimate_duration_from_word_count(
    word_count: int,
    words_per_second: float = 3.0,
    min_duration: float = 3.0,
    max_duration: float = 10.0,
) -> float:
    """Estimates a comfortable clip duration from how much text is in the
    captured scene, so a dense dashboard gets more time on screen than a
    near-empty splash page. Clamped to [min_duration, max_duration]."""
    if word_count <= 0 or words_per_second <= 0:
        return min_duration
    estimated = word_count / words_per_second
    return max(min_duration, min(max_duration, estimated))


def ensure_parent_dir(path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def gather_output_paths(base_dir: Path | str) -> tuple[Path, Path]:
    base_path = Path(base_dir)
    screenshot_path = base_path / "capture.png"
    video_path = base_path / "motion.mp4"
    return screenshot_path, video_path


# Ken Burns-style motion presets available to `build_ffmpeg_command`. All are
# single-pass `zoompan` filters (cheap on modest hardware, no extra decode
# passes). "static" is an escape hatch for scenes that shouldn't move (e.g.
# dense, text-heavy dashboards where camera motion would hurt readability).
MOTION_PRESETS: tuple[str, ...] = (
    "zoom_in",
    "zoom_out",
    "pan_left_to_right",
    "pan_right_to_left",
    "pan_top_to_bottom",
    "pan_bottom_to_top",
    "static",
)

# Fixed mild zoom used by the pan presets: just enough headroom for the crop
# window to slide across the frame without the source image running out of
# pixels at the edges.
_PAN_ZOOM = 1.15

# Centers the crop window on each axis; used by presets that don't move
# along that axis.
_CENTERED_X = "iw/2-(iw/zoom/2)"
_CENTERED_Y = "ih/2-(ih/zoom/2)"


def build_ffmpeg_command(
    input_path: Path | str,
    output_path: Path | str,
    duration: float,
    width: int = 1280,
    height: int = 720,
    motion_preset: str = "zoom_in",
) -> list[str]:
    if motion_preset not in MOTION_PRESETS:
        raise ValueError(
            f"Unknown motion_preset {motion_preset!r}. Expected one of: "
            f"{', '.join(MOTION_PRESETS)}"
        )

    source = str(input_path)
    destination = str(output_path)
    fps = 30
    # Total output frames, used so pan expressions can move linearly across
    # the frame over the exact clip duration instead of drifting forever.
    last_frame = max(round(float(duration) * fps) - 1, 1)

    x_expr: str | None = None
    y_expr: str | None = None

    if motion_preset == "zoom_in":
        # Kept identical to the original expression for backward compatibility.
        z_expr = "min(zoom+0.0001,1.3)"
    elif motion_preset == "zoom_out":
        z_expr = "if(eq(on,0),1.3,max(zoom-0.0001,1.0))"
        x_expr, y_expr = _CENTERED_X, _CENTERED_Y
    elif motion_preset == "pan_left_to_right":
        z_expr = str(_PAN_ZOOM)
        x_expr, y_expr = f"(iw-iw/zoom)*on/{last_frame}", _CENTERED_Y
    elif motion_preset == "pan_right_to_left":
        z_expr = str(_PAN_ZOOM)
        x_expr, y_expr = f"(iw-iw/zoom)*(1-on/{last_frame})", _CENTERED_Y
    elif motion_preset == "pan_top_to_bottom":
        z_expr = str(_PAN_ZOOM)
        x_expr, y_expr = _CENTERED_X, f"(ih-ih/zoom)*on/{last_frame}"
    elif motion_preset == "pan_bottom_to_top":
        z_expr = str(_PAN_ZOOM)
        x_expr, y_expr = _CENTERED_X, f"(ih-ih/zoom)*(1-on/{last_frame})"
    else:  # static
        z_expr = "1"
        x_expr, y_expr = _CENTERED_X, _CENTERED_Y

    zoompan_parts = [f"z='{z_expr}'"]
    if x_expr is not None:
        zoompan_parts.append(f"x='{x_expr}'")
    if y_expr is not None:
        zoompan_parts.append(f"y='{y_expr}'")
    zoompan_parts.append(f"d=1:s={width}x{height}:fps={fps}")

    zoom_filter = f"scale={width}:{height}," + "zoompan=" + ":".join(zoompan_parts)

    return [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        source,
        "-vf",
        zoom_filter,
        "-t",
        str(float(duration)),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        destination,
    ]


def build_capture_command(
    url: str,
    username: str = "",
    password: str = "",
    target_path: str = "",
    output_dir: str = "artifacts/login_job",
    width: int = 1280,
    height: int = 720,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pipeline.first_render",
        "--url",
        url,
        "--base-dir",
        str(output_dir),
        "--width",
        str(width),
        "--height",
        str(height),
    ]

    if username:
        command.extend(["--username", username])
    if password:
        command.extend(["--password", password])
    if target_path:
        command.extend(["--target-path", target_path])

    return command


def _fill_login_field(page, selector_candidates: tuple[str, ...], value: str) -> bool:
    if not value:
        return False

    for selector in selector_candidates:
        locator = page.locator(selector).first
        count = locator.count()
        if count > 0:
            try:
                locator.fill(value)
                return True
            except Exception:
                continue

    return False


def _click_login_button(page) -> None:
    for selector in LOGIN_BUTTON_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.click(timeout=10000)
                return
        except Exception:
            continue

    raise CaptureError(
        "Login fields were filled but no login/submit button could be found. "
        f"Tried selectors: {', '.join(LOGIN_BUTTON_SELECTORS)}"
    )


def _first_matching_selector(page, selector_candidates: tuple[str, ...]) -> str | None:
    for selector in selector_candidates:
        try:
            if page.locator(selector).first.count() > 0:
                return selector
        except Exception:
            continue
    return None


def _detect_page_context(page) -> PageContext:
    """Inspects the current page before any action is taken on it, so the
    capture flow "understands the platform" instead of blindly guessing."""
    email_selector = _first_matching_selector(page, EMAIL_SELECTORS)
    password_selector = _first_matching_selector(page, PASSWORD_SELECTORS)
    return PageContext(
        title=page.title(),
        url=page.url,
        has_login_form=password_selector is not None,
        email_selector=email_selector,
        password_selector=password_selector,
    )


def _open_login_form(page, timeout_ms: float = 8000, poll_interval_ms: float = 250) -> bool:
    """Many sites don't show a login form on the landing page itself; a
    'Log in' / 'Sign in' link or button has to be clicked first to reveal a
    modal or navigate to a dedicated /login page. Returns True if a plausible
    entry point was found and clicked, regardless of whether a form actually
    appeared afterwards.

    Client-rendered apps (Vue/Nuxt/Next, etc.) often lazy-load the login
    route's JS/CSS chunk after the click, so a single `networkidle` wait right
    after clicking can resolve before that chunk request even starts. Instead,
    this polls for the URL changing or a password field appearing, which is
    more reliable than a single fixed wait.
    """
    pre_click_url = page.url
    clicked = False

    for selector in LOGIN_ENTRY_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0 or not locator.is_visible():
                continue
            locator.click(timeout=10000)
        except Exception:
            continue
        else:
            clicked = True
            break

    if not clicked:
        return False

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if page.url != pre_click_url or _first_matching_selector(page, PASSWORD_SELECTORS):
            break
        page.wait_for_timeout(poll_interval_ms)

    _wait_for_network_idle(page)
    return True


def _wait_for_network_idle(page, timeout: float = 5000) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        # Best-effort: some pages keep background connections (polling,
        # websockets) open forever, which would otherwise time this out.
        pass


def _verify_login_success(
    page,
    pre_login_url: str,
    password_selector: str | None,
    timeout_ms: float = 15000,
    poll_interval_ms: float = 250,
) -> None:
    """Confirms the login action actually completed instead of assuming a
    click succeeded. Success is signaled by the URL changing or the password
    field disappearing; an error message on the page fails fast instead."""
    deadline = time.monotonic() + timeout_ms / 1000

    while True:
        for selector in LOGIN_ERROR_SELECTORS:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0 and locator.is_visible():
                    message = locator.inner_text().strip()
                    if message and LOGIN_ERROR_TEXT_PATTERN.search(message):
                        raise LoginVerificationError(
                            f"Login appears to have failed: {message}"
                        )
            except LoginVerificationError:
                raise
            except Exception:
                continue

        url_changed = page.url != pre_login_url
        password_gone = True
        if password_selector:
            try:
                locator = page.locator(password_selector).first
                password_gone = locator.count() == 0 or not locator.is_visible()
            except Exception:
                password_gone = True

        if url_changed or password_gone:
            return

        if time.monotonic() >= deadline:
            raise LoginVerificationError(
                "Timed out waiting to verify whether login succeeded: the page "
                "URL did not change and the password field is still visible."
            )
        page.wait_for_timeout(poll_interval_ms)


def _hide_elements(page, selectors: list[str]) -> None:
    if not selectors:
        return
    rules = "\n".join(f"{selector} {{ visibility: hidden !important; }}" for selector in selectors)
    page.add_style_tag(content=rules)


def _extract_scene_text(page, selector: str = "") -> str:
    locator = page.locator(selector).first if selector else page.locator("body").first
    try:
        return locator.inner_text(timeout=5000)
    except Exception:
        return ""


def capture_page(
    url: str,
    output_path: Path | str,
    width: int = 1280,
    height: int = 720,
    device_scale_factor: int = 1,
    username: str = "",
    password: str = "",
    target_path: str = "",
    capture_selector: str = "",
    extra_hide_selectors: tuple[str, ...] | list[str] = (),
    hide_common_overlays: bool = True,
    words_per_second: float = 3.0,
    min_duration: float = 3.0,
    max_duration: float = 10.0,
) -> CaptureResult:
    from playwright.sync_api import sync_playwright

    target = ensure_parent_dir(output_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=device_scale_factor,
        )
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        _wait_for_network_idle(page)

        # Understand the platform before acting on it: is this actually a
        # login page, and which fields does it expose?
        context = _detect_page_context(page)
        login_verified = False

        if username or password:
            if not context.has_login_form:
                # The landing page itself may not show a login form; try
                # clicking a 'Log in'/'Sign in' entry point (modal trigger or
                # link to a dedicated /login page) before giving up.
                if _open_login_form(page):
                    context = _detect_page_context(page)

            if not context.has_login_form:
                browser.close()
                raise CaptureError(
                    f"Login was requested for {url!r} but no password field was "
                    "found on the page (including after trying to click a "
                    "'Log in'/'Sign in' link), so the login form could not be "
                    "identified. Pass --target-path or a direct login URL if "
                    "the form lives elsewhere."
                )

            pre_login_url = page.url
            if username:
                _fill_login_field(page, EMAIL_SELECTORS, username)
            if password:
                _fill_login_field(page, PASSWORD_SELECTORS, password)
            _click_login_button(page)
            _verify_login_success(page, pre_login_url, context.password_selector)
            login_verified = True

        if target_path:
            if target_path.startswith("http://") or target_path.startswith("https://"):
                next_url = target_path
            else:
                next_url = urljoin(url.rstrip("/") + "/", target_path.lstrip("/"))
            page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
            _wait_for_network_idle(page)

        # Decide what NOT to record: hide noisy overlays (cookie/consent
        # banners by default, plus anything the caller wants hidden) before
        # the screenshot is taken.
        hide_selectors = list(DEFAULT_HIDE_SELECTORS) if hide_common_overlays else []
        hide_selectors.extend(extra_hide_selectors)
        _hide_elements(page, hide_selectors)

        # Decide what TO record: either a specific element/region, or the
        # full viewport.
        if capture_selector:
            locator = page.locator(capture_selector).first
            locator.wait_for(state="visible", timeout=15000)
            locator.screenshot(path=str(target))
        else:
            page.screenshot(path=str(target), full_page=False)

        scene_text = _extract_scene_text(page, capture_selector)
        page_title = page.title()
        browser.close()

    word_count = len(scene_text.split())
    duration = estimate_duration_from_word_count(
        word_count,
        words_per_second=words_per_second,
        min_duration=min_duration,
        max_duration=max_duration,
    )

    return CaptureResult(
        screenshot_path=target,
        duration=duration,
        word_count=word_count,
        page_title=page_title,
        login_verified=login_verified,
    )


def render_motion_video(
    input_path: Path | str,
    output_path: Path | str,
    duration: float = 4.0,
    width: int = 1280,
    height: int = 720,
    motion_preset: str = "zoom_in",
) -> Path:
    target = ensure_parent_dir(output_path)
    command = build_ffmpeg_command(
        input_path=input_path,
        output_path=target,
        duration=duration,
        width=width,
        height=height,
        motion_preset=motion_preset,
    )
    subprocess.run(command, check=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a product page and render a short zoom-motion clip.")
    parser.add_argument("--url", default="http://localhost:5173", help="URL to capture")
    parser.add_argument("--base-dir", default="artifacts/first_scene", help="Directory for the captured screenshot and rendered video")
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Clip duration in seconds. If omitted, duration is estimated from how much text is in the captured scene.",
    )
    parser.add_argument("--width", type=int, default=1280, help="Capture width in pixels")
    parser.add_argument("--height", type=int, default=720, help="Capture height in pixels")
    parser.add_argument("--username", default="", help="Optional username or email for a login flow")
    parser.add_argument(
        "--password",
        default="",
        help=(
            "Optional password for a login flow. Prefer the MPOSTELE_PASSWORD "
            "environment variable instead of this flag so the value doesn't "
            "appear in process listings (ps/tasklist)."
        ),
    )
    parser.add_argument("--target-path", default="", help="Optional page path to navigate after login")
    parser.add_argument(
        "--capture-selector",
        default="",
        help="Optional CSS selector to screenshot instead of the full viewport (what to record).",
    )
    parser.add_argument(
        "--hide-selector",
        action="append",
        default=[],
        dest="hide_selectors",
        help="Additional CSS selector to hide before capturing (what NOT to record). Repeatable.",
    )
    parser.add_argument(
        "--no-hide-overlays",
        action="store_false",
        dest="hide_common_overlays",
        default=True,
        help="Don't automatically hide common cookie/consent banners.",
    )
    parser.add_argument(
        "--words-per-second",
        type=float,
        default=3.0,
        help="Assumed reading speed used to estimate clip duration when --duration is omitted.",
    )
    parser.add_argument("--min-duration", type=float, default=3.0, help="Lower bound for the estimated clip duration")
    parser.add_argument("--max-duration", type=float, default=10.0, help="Upper bound for the estimated clip duration")
    parser.add_argument(
        "--motion-preset",
        default="zoom_in",
        choices=MOTION_PRESETS,
        help="Ken Burns-style camera motion to apply to the captured screenshot.",
    )
    args = parser.parse_args()

    password = args.password or os.environ.get("MPOSTELE_PASSWORD", "")

    image_path, video_path = gather_output_paths(args.base_dir)
    result = capture_page(
        args.url,
        image_path,
        width=args.width,
        height=args.height,
        username=args.username,
        password=password,
        target_path=args.target_path,
        capture_selector=args.capture_selector,
        extra_hide_selectors=args.hide_selectors,
        hide_common_overlays=args.hide_common_overlays,
        words_per_second=args.words_per_second,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
    )

    duration = args.duration if args.duration is not None else result.duration
    render_motion_video(
        result.screenshot_path,
        video_path,
        duration=duration,
        width=args.width,
        height=args.height,
        motion_preset=args.motion_preset,
    )
    print(
        f"Captured {result.screenshot_path} ({result.word_count} words, "
        f"login_verified={result.login_verified}) and rendered {video_path} at {duration:.1f}s "
        f"using the '{args.motion_preset}' motion preset."
    )


if __name__ == "__main__":
    main()
