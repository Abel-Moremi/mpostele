from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin


def ensure_parent_dir(path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def gather_output_paths(base_dir: Path | str) -> tuple[Path, Path]:
    base_path = Path(base_dir)
    screenshot_path = base_path / "capture.png"
    video_path = base_path / "motion.mp4"
    return screenshot_path, video_path


def build_ffmpeg_command(
    input_path: Path | str,
    output_path: Path | str,
    duration: float,
    width: int = 1280,
    height: int = 720,
) -> list[str]:
    source = str(input_path)
    destination = str(output_path)
    zoom_filter = (
        f"scale={width}:{height},"
        f"zoompan=z='min(zoom+0.0001,1.3)':d=1:s={width}x{height}:fps=30"
    )

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


def _fill_login_field(page, selector_candidates: list[str], value: str) -> bool:
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


def _click_login_button(page) -> bool:
    selectors = [
        "button:has-text('Log in')",
        "button:has-text('Login')",
        "button:has-text('Sign in')",
        "input[type='submit']",
        "button[type='submit']",
        "button[type='button']",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() > 0:
                locator.click(timeout=10000)
                return True
        except Exception:
            continue

    return False


def capture_page(
    url: str,
    output_path: Path | str,
    width: int = 1280,
    height: int = 720,
    device_scale_factor: int = 1,
    username: str = "",
    password: str = "",
    target_path: str = "",
) -> Path:
    from playwright.sync_api import sync_playwright

    target = ensure_parent_dir(output_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=device_scale_factor,
        )
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        if username or password:
            email_selectors = [
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "input[name='login']",
                "input[autocomplete='username']",
            ]
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[autocomplete='current-password']",
            ]

            if username:
                _fill_login_field(page, email_selectors, username)
            if password:
                _fill_login_field(page, password_selectors, password)
            _click_login_button(page)

        if target_path:
            if target_path.startswith("http://") or target_path.startswith("https://"):
                next_url = target_path
            else:
                next_url = urljoin(url.rstrip("/") + "/", target_path.lstrip("/"))
            page.goto(next_url, wait_until="domcontentloaded", timeout=60000)

        page.screenshot(path=str(target), full_page=False)
        browser.close()

    return target


def render_motion_video(
    input_path: Path | str,
    output_path: Path | str,
    duration: float = 4.0,
    width: int = 1280,
    height: int = 720,
) -> Path:
    target = ensure_parent_dir(output_path)
    command = build_ffmpeg_command(
        input_path=input_path,
        output_path=target,
        duration=duration,
        width=width,
        height=height,
    )
    subprocess.run(command, check=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture a product page and render a short zoom-motion clip.")
    parser.add_argument("--url", default="http://localhost:5173", help="URL to capture")
    parser.add_argument("--base-dir", default="artifacts/first_scene", help="Directory for the captured screenshot and rendered video")
    parser.add_argument("--duration", type=float, default=4.0, help="Clip duration in seconds")
    parser.add_argument("--width", type=int, default=1280, help="Capture width in pixels")
    parser.add_argument("--height", type=int, default=720, help="Capture height in pixels")
    parser.add_argument("--username", default="", help="Optional username or email for a login flow")
    parser.add_argument("--password", default="", help="Optional password for a login flow")
    parser.add_argument("--target-path", default="", help="Optional page path to navigate after login")
    args = parser.parse_args()

    image_path, video_path = gather_output_paths(args.base_dir)
    capture_page(
        args.url,
        image_path,
        width=args.width,
        height=args.height,
        username=args.username,
        password=args.password,
        target_path=args.target_path,
    )
    render_motion_video(image_path, video_path, duration=args.duration, width=args.width, height=args.height)
    print(f"Captured {image_path} and rendered {video_path}.")


if __name__ == "__main__":
    main()
