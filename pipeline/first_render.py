from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


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


def capture_page(
    url: str,
    output_path: Path | str,
    width: int = 1280,
    height: int = 720,
    device_scale_factor: int = 1,
) -> Path:
    from playwright.sync_api import sync_playwright

    target = ensure_parent_dir(output_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=device_scale_factor,
        )
        page.goto(url, wait_until="networkidle", timeout=60000)
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
    args = parser.parse_args()

    image_path, video_path = gather_output_paths(args.base_dir)
    capture_page(args.url, image_path, width=args.width, height=args.height)
    render_motion_video(image_path, video_path, duration=args.duration, width=args.width, height=args.height)
    print(f"Captured {image_path} and rendered {video_path}.")


if __name__ == "__main__":
    main()
