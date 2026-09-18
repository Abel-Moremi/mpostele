"""Smoke test for render_remote()'s HTTP client logic against a fake local
server standing in for the real Colab/ngrok endpoint - this can't reach an
actual Colab session, but it exercises the exact submit -> poll -> download
code path and the auth header, which is the part that's actually testable
without a live Wan2.1 GPU session.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_API_KEY = "test-shared-secret"
FAKE_VIDEO_BYTES = b"not a real mp4, just test bytes"
POLLS_BEFORE_DONE = 2

_poll_count = {"n": 0}


class FakeWan21Handler(BaseHTTPRequestHandler):
    def _check_auth(self) -> bool:
        if self.headers.get("x-api-key") != TEST_API_KEY:
            self.send_response(401)
            self.end_headers()
            return False
        return True

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self._check_auth():
            return
        if self.path == "/generate":
            self._send_json({"job_id": "fake_job_123"})
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if not self._check_auth():
            return
        if self.path == "/status/fake_job_123":
            _poll_count["n"] += 1
            status = "running" if _poll_count["n"] < POLLS_BEFORE_DONE else "done"
            self._send_json({"status": status, "error": None})
        elif self.path == "/result/fake_job_123":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(FAKE_VIDEO_BYTES)))
            self.end_headers()
            self.wfile.write(FAKE_VIDEO_BYTES)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # keep test output quiet


def main() -> None:
    server = HTTPServer(("127.0.0.1", 0), FakeWan21Handler)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()

    from app.config import settings
    from app.media.video_engine import render_remote

    settings.WAN21_REMOTE_ENDPOINT = f"http://127.0.0.1:{port}"
    settings.WAN21_API_KEY = TEST_API_KEY
    settings.WAN21_POLL_INTERVAL_SECONDS = 0.1
    settings.WAN21_POLL_TIMEOUT_SECONDS = 10

    job_state = {"keyframe_prompt": {"positive": "a test scene", "negative": "text, watermark"}}
    output_dir = settings.TMP_DIR / "remote_dispatch_probe"

    raw_clip = render_remote(job_state, output_dir)
    assert raw_clip.read_bytes() == FAKE_VIDEO_BYTES, "downloaded content didn't match fake server's bytes"
    assert _poll_count["n"] == POLLS_BEFORE_DONE, f"expected {POLLS_BEFORE_DONE} polls, got {_poll_count['n']}"
    print(f"submit -> poll ({_poll_count['n']}x) -> download: OK")
    print(f"wrote: {raw_clip}")

    # negative case: wrong API key should surface as an HTTP error, not silently succeed
    settings.WAN21_API_KEY = "wrong-key"
    try:
        render_remote(job_state, settings.TMP_DIR / "remote_dispatch_probe_2")
        print("FAIL: expected an auth error, got none")
    except Exception as exc:
        print(f"auth rejection surfaced correctly: {type(exc).__name__}")

    raw_clip.parent.parent.mkdir(exist_ok=True)
    import shutil

    shutil.rmtree(settings.TMP_DIR / "remote_dispatch_probe", ignore_errors=True)
    shutil.rmtree(settings.TMP_DIR / "remote_dispatch_probe_2", ignore_errors=True)
    server.shutdown()


if __name__ == "__main__":
    main()
