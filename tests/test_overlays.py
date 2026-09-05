import unittest
from pathlib import Path

from pipeline.overlays import (
    build_manim_command,
    build_overlay_composite_command,
    expected_overlay_output_path,
    OVERLAY_SCENES,
)


class OverlaysTests(unittest.TestCase):
    def test_build_manim_command_rejects_unknown_overlay_type(self):
        with self.assertRaises(ValueError):
            build_manim_command("not-a-real-overlay", media_dir="artifacts/overlays")

    def test_build_manim_command_uses_transparent_and_scene_name(self):
        cmd = build_manim_command("title", media_dir="artifacts/overlays", width=1280, height=720)
        joined = " ".join(cmd)

        self.assertIn("manim_scenes.py", joined)
        self.assertIn("TitleOverlayScene", joined)
        self.assertIn("--transparent", cmd)
        self.assertIn("1280,720", joined)

    def test_build_manim_command_callout_uses_callout_scene(self):
        cmd = build_manim_command("callout", media_dir="artifacts/overlays")
        self.assertIn("CalloutOverlayScene", " ".join(cmd))

    def test_all_overlay_scenes_buildable(self):
        for overlay_type in OVERLAY_SCENES:
            cmd = build_manim_command(overlay_type, media_dir="artifacts/overlays")
            self.assertIn("--transparent", cmd)

    def test_expected_overlay_output_path_matches_manim_convention(self):
        path = expected_overlay_output_path("artifacts/overlays", height=720, frame_rate=30, output_file="title")
        self.assertEqual(
            path,
            Path("artifacts/overlays") / "videos" / "manim_scenes" / "720p30" / "title.mov",
        )

    def test_build_overlay_composite_command_uses_overlay_filter(self):
        cmd = build_overlay_composite_command(
            base_video=Path("artifacts/first_scene/motion.mp4"),
            overlay_video=Path("artifacts/overlays/title.mov"),
            output_path=Path("outputs/final.mp4"),
        )
        joined = " ".join(cmd)

        self.assertIn("motion.mp4", joined)
        self.assertIn("title.mov", joined)
        self.assertIn("overlay=format=auto", joined)
        self.assertIn("final.mp4", joined)


if __name__ == "__main__":
    unittest.main()
