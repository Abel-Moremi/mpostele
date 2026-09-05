import unittest
from pathlib import Path

from pipeline.first_render import (
    build_capture_command,
    build_ffmpeg_command,
    build_transcode_command,
    capture_motion_sequence,
    ensure_parent_dir,
    estimate_duration_from_word_count,
    gather_output_paths,
    LOGIN_ERROR_TEXT_PATTERN,
    MOTION_PRESETS,
    MOTION_TRIGGERS,
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

    def test_build_ffmpeg_command_zoom_in_matches_original_expression(self):
        # Regression test: the default preset must keep the exact expression
        # used before motion presets were introduced.
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
        )
        self.assertIn("z='min(zoom+0.0001,1.3)'", " ".join(cmd))

    def test_build_ffmpeg_command_zoom_out_eases_back_to_original_size(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            motion_preset="zoom_out",
        )
        self.assertIn("max(zoom-0.0001,1.0)", " ".join(cmd))

    def test_build_ffmpeg_command_pan_left_to_right_moves_x_forward(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            motion_preset="pan_left_to_right",
        )
        self.assertIn("(iw-iw/zoom)*on", " ".join(cmd))

    def test_build_ffmpeg_command_pan_right_to_left_moves_x_backward(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            motion_preset="pan_right_to_left",
        )
        self.assertIn("(iw-iw/zoom)*(1-on", " ".join(cmd))

    def test_build_ffmpeg_command_pan_top_to_bottom_moves_y_forward(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            motion_preset="pan_top_to_bottom",
        )
        self.assertIn("(ih-ih/zoom)*on", " ".join(cmd))

    def test_build_ffmpeg_command_pan_bottom_to_top_moves_y_backward(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            motion_preset="pan_bottom_to_top",
        )
        self.assertIn("(ih-ih/zoom)*(1-on", " ".join(cmd))

    def test_build_ffmpeg_command_static_has_no_zoom_change(self):
        cmd = build_ffmpeg_command(
            input_path=Path("assets/source.png"),
            output_path=Path("outputs/scene.mp4"),
            duration=4.0,
            motion_preset="static",
        )
        self.assertIn("z='1'", " ".join(cmd))

    def test_build_ffmpeg_command_rejects_unknown_preset(self):
        with self.assertRaises(ValueError):
            build_ffmpeg_command(
                input_path=Path("assets/source.png"),
                output_path=Path("outputs/scene.mp4"),
                duration=4.0,
                motion_preset="not-a-real-preset",
            )

    def test_motion_presets_all_buildable(self):
        for preset in MOTION_PRESETS:
            cmd = build_ffmpeg_command(
                input_path=Path("assets/source.png"),
                output_path=Path("outputs/scene.mp4"),
                duration=4.0,
                motion_preset=preset,
            )
            self.assertIn("zoompan", " ".join(cmd))

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

    def test_estimate_duration_from_word_count_clamps_to_min(self):
        duration = estimate_duration_from_word_count(0, words_per_second=3.0, min_duration=3.0, max_duration=10.0)
        self.assertEqual(duration, 3.0)

    def test_estimate_duration_from_word_count_clamps_to_max(self):
        duration = estimate_duration_from_word_count(1000, words_per_second=3.0, min_duration=3.0, max_duration=10.0)
        self.assertEqual(duration, 10.0)

    def test_estimate_duration_from_word_count_scales_with_content(self):
        duration = estimate_duration_from_word_count(15, words_per_second=3.0, min_duration=3.0, max_duration=10.0)
        self.assertEqual(duration, 5.0)

    def test_login_error_pattern_ignores_benign_page_titles(self):
        # Regression test: frameworks like Nuxt/Vue insert an accessibility
        # "route announcer" with role="alert" that just echoes the page
        # title. That must not be mistaken for a real login error.
        self.assertIsNone(LOGIN_ERROR_TEXT_PATTERN.search("Sign In - DreamCraftr"))
        self.assertIsNone(LOGIN_ERROR_TEXT_PATTERN.search("Dashboard - DreamCraftr"))

    def test_login_error_pattern_matches_real_error_messages(self):
        self.assertIsNotNone(LOGIN_ERROR_TEXT_PATTERN.search("Invalid email or password"))
        self.assertIsNotNone(LOGIN_ERROR_TEXT_PATTERN.search("Incorrect password, please try again"))
        self.assertIsNotNone(LOGIN_ERROR_TEXT_PATTERN.search("Login failed"))

    def test_build_transcode_command_reencodes_to_h264_mp4(self):
        cmd = build_transcode_command(
            input_path=Path("artifacts/motion_job/motion_sequence.webm"),
            output_path=Path("artifacts/motion_job/motion.mp4"),
        )
        joined = " ".join(cmd)

        self.assertIn("motion_sequence.webm", joined)
        self.assertIn("motion.mp4", joined)
        self.assertIn("libx264", cmd)

    def test_motion_triggers_include_expected_options(self):
        self.assertEqual(set(MOTION_TRIGGERS), {"hover", "click", "scroll", "none"})

    def test_capture_motion_sequence_rejects_unknown_trigger(self):
        with self.assertRaises(ValueError):
            capture_motion_sequence(
                url="http://localhost:5173",
                output_dir="artifacts/motion_job",
                motion_trigger="not-a-real-trigger",
            )


if __name__ == "__main__":
    unittest.main()
