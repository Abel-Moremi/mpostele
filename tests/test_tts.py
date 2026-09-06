import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.tts import TTSError, synthesis_key, synthesize_speech


class FakePipeline:
    def __init__(self):
        self.calls = 0

    def __call__(self, text, **settings):
        self.calls += 1
        yield text, "phonemes", [0.0, 0.25, -0.25]


class TTSTests(unittest.TestCase):
    def test_synthesis_key_is_stable_and_tracks_voice_settings(self):
        first = synthesis_key("Hello", "af_heart", 1.0, "a")
        self.assertEqual(first, synthesis_key("Hello", "af_heart", 1, "a"))
        self.assertNotEqual(first, synthesis_key("Hello", "af_sky", 1.0, "a"))
        self.assertNotEqual(first, synthesis_key("Hello", "af_heart", 1.1, "a"))

    def test_reuses_matching_cached_output_without_loading_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "voice.wav"
            output.write_bytes(b"existing")
            output.with_suffix(".wav.tts-cache.json").write_text(
                json.dumps({"key": synthesis_key("Hello")}), encoding="utf-8"
            )

            self.assertEqual(synthesize_speech("Hello", output), output)
            self.assertEqual(output.read_bytes(), b"existing")

    def test_rejects_invalid_input_before_importing_optional_dependencies(self):
        with self.assertRaises(ValueError):
            synthesize_speech("  ", "voice.wav")
        with self.assertRaises(ValueError):
            synthesize_speech("Hello", "voice.wav", speed=0)

    def test_reports_optional_install_command_when_dependencies_are_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict("sys.modules", {"numpy": None}):
                with self.assertRaisesRegex(TTSError, "requirements-tts.txt"):
                    synthesize_speech("Hello", Path(temp) / "voice.wav")


if __name__ == "__main__":
    unittest.main()
