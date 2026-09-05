import unittest
from pathlib import Path

from pipeline.first_render import (
    build_capture_command,
    build_ffmpeg_command,
    ensure_parent_dir,
    gather_output_paths,
)


class FirstRenderTests(unittest.TestCase):
    def test_build_ffmpeg_command_uses_zoompan_and_mp4_output(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            width=1280,
            height=720,
        )

        self.assertIn("zoompan", " ".join(cmd))
        self.assertIn("scene.mp4", " ".join(cmd))
        self.assertIn("libx264", " ".join(cmd))

    def test_ensure_parent_dir_creates_directories(self):
        target = Path("outputs/test/demo/out.mp4")
        ensure_parent_dir(target)
        self.assertTrue(target.parent.exists())

    def test_gather_output_paths_creates_expected_names(self):
        base_dir = Path("demo")
        screenshot_path, video_path = gather_output_paths(base_dir)

        self.assertEqual(screenshot_path.name, "capture.png")
        self.assertEqual(video_path.name, "motion.mp4")

    def test_build_capture_command_includes_credentials_and_target_url(self):
        cmd = build_capture_command(
            url="https://example.com/login",
            username="user@example.com",
            password="secret123",
            target_path="/dashboard",
            output_dir="artifacts/login_job",
        )

        self.assertIn("--url", cmd)
        self.assertIn("https://example.com/login", cmd)
        self.assertIn("--username", cmd)
        self.assertIn("user@example.com", cmd)
        self.assertIn("--password", cmd)
        self.assertIn("secret123", cmd)
        self.assertIn("--target-path", cmd)
        self.assertIn("/dashboard", cmd)


if __name__ == "__main__":
    unittest.main()
