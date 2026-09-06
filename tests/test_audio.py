import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.audio import (
    AudioError,
    build_audio_composite_command,
    build_ffprobe_command,
    probe_audio_duration,
)


class AudioTests(unittest.TestCase):
    def test_build_ffprobe_command_selects_first_audio_stream(self):
        cmd = build_ffprobe_command(Path("artifacts/demo/voiceover.wav"))

        self.assertEqual(cmd[0], "ffprobe")
        self.assertIn("a:0", cmd)
        self.assertIn("voiceover.wav", " ".join(cmd))

    def test_probe_audio_duration_reads_stream_duration(self):
        completed = type("Completed", (), {"stdout": json.dumps({"streams": [{"duration": "4.25"}]})})()
        with patch("pipeline.audio.subprocess.run", return_value=completed):
            self.assertEqual(probe_audio_duration("voiceover.wav"), 4.25)

    def test_probe_audio_duration_falls_back_to_format_duration(self):
        completed = type(
            "Completed",
            (),
            {"stdout": json.dumps({"streams": [{"duration": "N/A"}], "format": {"duration": "3.5"}})},
        )()
        with patch("pipeline.audio.subprocess.run", return_value=completed):
            self.assertEqual(probe_audio_duration("voiceover.wav"), 3.5)

    def test_probe_audio_duration_rejects_missing_duration(self):
        completed = type("Completed", (), {"stdout": json.dumps({"streams": []})})()
        with patch("pipeline.audio.subprocess.run", return_value=completed):
            with self.assertRaises(AudioError):
                probe_audio_duration("voiceover.wav")

    def test_composite_command_matches_video_to_narration(self):
        cmd = build_audio_composite_command(
            video_path="artifacts/demo/motion.mp4",
            audio_path="artifacts/demo/voiceover.wav",
            output_path="artifacts/demo/final.mp4",
            duration=5.25,
        )
        joined = " ".join(cmd)

        self.assertIn("tpad=stop_mode=clone", joined)
        self.assertIn("trim=duration=5.250000", joined)
        self.assertIn("atrim=duration=5.250000", joined)
        self.assertIn("loudnorm=I=-16", joined)
        self.assertIn("libx264", cmd)
        self.assertIn("aac", cmd)
        self.assertIn("48000", cmd)
        self.assertEqual(cmd[-1], "artifacts/demo/final.mp4")

    def test_composite_command_can_skip_normalization(self):
        cmd = build_audio_composite_command("video.mp4", "voice.wav", "final.mp4", 3, False)
        self.assertNotIn("loudnorm", " ".join(cmd))

    def test_composite_command_rejects_non_positive_duration(self):
        with self.assertRaises(ValueError):
            build_audio_composite_command("video.mp4", "voice.wav", "final.mp4", 0)


if __name__ == "__main__":
    unittest.main()
