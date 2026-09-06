import tempfile
import unittest
from pathlib import Path

from pipeline.validate_export import (
    ExportExpectations,
    build_probe_command,
    has_faststart,
    validate_metadata,
)


def compatible_metadata() -> dict:
    return {
        "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "12.500000"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "pix_fmt": "yuv420p",
                "width": 1080,
                "height": 1920,
                "r_frame_rate": "30/1",
                "avg_frame_rate": "30/1",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
        ],
    }


class ValidateExportTests(unittest.TestCase):
    def test_build_probe_command_requests_streams_and_format(self):
        command = build_probe_command("output.mp4")
        self.assertEqual(command[0], "ffprobe")
        self.assertIn("-show_streams", command)
        self.assertIn("-show_format", command)
        self.assertEqual(command[-1], "output.mp4")

    def test_accepts_platform_compatible_vertical_export(self):
        result = validate_metadata(
            "output.mp4",
            compatible_metadata(),
            ExportExpectations(width=1080, height=1920, fps=30),
            faststart=True,
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.errors, ())
        self.assertEqual(result.summary["duration_seconds"], 12.5)

    def test_uses_nominal_rate_for_narration_timed_concat(self):
        metadata = compatible_metadata()
        metadata["streams"][0]["avg_frame_rate"] = "370000/12372"
        result = validate_metadata(
            "output.mp4",
            metadata,
            ExportExpectations(width=1080, height=1920, fps=30),
            faststart=True,
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.summary["fps"], 30.0)
        self.assertAlmostEqual(result.summary["average_fps"], 29.906, places=3)

    def test_rejects_non_finite_or_non_positive_expected_fps(self):
        for fps in (float("nan"), float("inf"), float("-inf"), 0, -1):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                ExportExpectations(fps=fps)

    def test_reports_incompatible_video_and_audio(self):
        metadata = compatible_metadata()
        metadata["streams"][0].update({"codec_name": "hevc", "pix_fmt": "yuv444p", "width": 720})
        metadata["streams"][1].update({"codec_name": "mp3", "sample_rate": "44100", "channels": 1})
        result = validate_metadata(
            "output.mp4",
            metadata,
            ExportExpectations(width=1080, height=1920, fps=30),
            faststart=False,
        )
        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.errors), 7)

    def test_rejects_non_finite_duration(self):
        metadata = compatible_metadata()
        metadata["format"]["duration"] = "inf"
        result = validate_metadata(
            "output.mp4",
            metadata,
            ExportExpectations(require_faststart=False),
            faststart=None,
        )
        self.assertFalse(result.valid)
        self.assertIn("duration", " ".join(result.errors).lower())

    def test_can_allow_missing_audio(self):
        metadata = compatible_metadata()
        metadata["streams"] = metadata["streams"][:1]
        result = validate_metadata(
            "output.mp4",
            metadata,
            ExportExpectations(require_audio=False, require_faststart=False),
            faststart=None,
        )
        self.assertTrue(result.valid)
        self.assertIn("No audio stream", result.warnings[0])

    def test_detects_faststart_atom_order(self):
        def atom(kind: bytes, payload: bytes = b"") -> bytes:
            return (8 + len(payload)).to_bytes(4, "big") + kind + payload

        with tempfile.TemporaryDirectory() as temp:
            fast = Path(temp) / "fast.mp4"
            slow = Path(temp) / "slow.mp4"
            fast.write_bytes(atom(b"ftyp") + atom(b"moov") + atom(b"mdat"))
            slow.write_bytes(atom(b"ftyp") + atom(b"mdat") + atom(b"moov"))
            self.assertTrue(has_faststart(fast))
            self.assertFalse(has_faststart(slow))


if __name__ == "__main__":
    unittest.main()
