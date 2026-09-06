import json
import tempfile
import unittest
from pathlib import Path

from pipeline.render_job import (
    RenderJobError,
    build_concat_command,
    build_duration_probe_command,
    build_scene_normalize_command,
    load_render_job,
)


class RenderJobTests(unittest.TestCase):
    def _write_manifest(self, folder: Path, data: dict) -> Path:
        path = folder / "job.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_loads_vertical_multi_scene_job_and_resolves_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            manifest = self._write_manifest(
                folder,
                {
                    "output": "outputs/demo.mp4",
                    "work_dir": "artifacts/demo",
                    "export": {"preset": "vertical_1080p", "fps": 30},
                    "scenes": [
                        {"id": "intro", "url": "http://localhost:5173", "motion_preset": "zoom_in"},
                        {"id": "feature", "image": "assets/feature.png", "duration": 4},
                    ],
                },
            )

            job = load_render_job(manifest)

            self.assertEqual((job.export.width, job.export.height), (1080, 1920))
            self.assertEqual(job.export.output, (folder / "outputs/demo.mp4").resolve())
            self.assertEqual(job.scenes[1].source, (folder / "assets/feature.png").resolve())
            self.assertEqual(len(job.scenes), 2)

    def test_loads_utf8_manifest_with_bom(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            manifest = folder / "job.json"
            manifest.write_text(
                json.dumps({"scenes": [{"video": "demo.mp4"}]}),
                encoding="utf-8-sig",
            )
            self.assertEqual(len(load_render_job(manifest).scenes), 1)

    def test_requires_exactly_one_scene_source(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self._write_manifest(
                Path(temp),
                {"scenes": [{"url": "https://example.com", "video": "demo.mp4"}]},
            )
            with self.assertRaises(RenderJobError):
                load_render_job(manifest)

    def test_rejects_duplicate_scene_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self._write_manifest(
                Path(temp),
                {"scenes": [{"id": "same", "image": "a.png"}, {"id": "same", "image": "b.png"}]},
            )
            with self.assertRaises(RenderJobError):
                load_render_job(manifest)

    def test_rejects_plaintext_password_in_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self._write_manifest(
                Path(temp),
                {"scenes": [{"url": "https://example.com", "capture": {"password": "secret"}}]},
            )
            with self.assertRaises(RenderJobError):
                load_render_job(manifest)

    def test_validates_overlay_text(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = self._write_manifest(
                Path(temp),
                {"scenes": [{"image": "a.png", "overlay": {"type": "title"}}]},
            )
            with self.assertRaises(RenderJobError):
                load_render_job(manifest)

    def test_normalize_command_adds_silence_when_scene_has_no_audio(self):
        command = build_scene_normalize_command("scene.mp4", "normalized.mp4", 1080, 1920, 30, False)
        joined = " ".join(command)
        self.assertIn("anullsrc", joined)
        self.assertIn("scale=1080:1920", joined)
        self.assertIn("1:a:0", command)
        self.assertEqual(command[-1], "normalized.mp4")

    def test_normalize_command_preserves_existing_audio(self):
        command = build_scene_normalize_command("scene.mp4", "normalized.mp4", 1280, 720, 24, True)
        self.assertNotIn("anullsrc", " ".join(command))
        self.assertIn("0:a:0", command)
        self.assertIn("aresample=48000", " ".join(command))

    def test_normalize_command_can_trim_to_scene_duration(self):
        command = build_scene_normalize_command(
            "scene.mp4", "normalized.mp4", 1280, 720, 30, True, duration=3.5
        )
        self.assertIn("3.500000", command)
        self.assertEqual(command[-1], "normalized.mp4")

    def test_duration_probe_command_reads_container_duration(self):
        command = build_duration_probe_command("scene.mp4")
        self.assertEqual(command[0], "ffprobe")
        self.assertIn("format=duration", command)
        self.assertEqual(command[-1], "scene.mp4")

    def test_concat_command_stream_copies_normalized_scenes(self):
        command = build_concat_command("concat.txt", "final.mp4")
        self.assertIn("concat", command)
        self.assertIn("copy", command)
        self.assertIn("+faststart", command)
        self.assertEqual(command[-1], "final.mp4")


if __name__ == "__main__":
    unittest.main()
