# Commands

This note should hold the practical terminal commands used in the project.

## Ollama

```bash
ollama pull qwen2.5:1.5b
ollama serve
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:1.5b", "keep_alive": 0}'
```

## Diffusion (example, adjust to actual entry script)

```bash
python -m app.media.poster_engine --job job_01H123456789
python -m app.media.video_engine --job job_01H123456789
```

## Remote video dispatch (Wan2.1 via Colab)

```bash
# after opening colab/wan21_server.ipynb and running all cells, copy its printed URL:
export WAN21_REMOTE_ENDPOINT="https://<something>.ngrok-free.app"
export WAN21_API_KEY="<same value as the notebook's API_KEY cell>"

# verify the client logic without a live Colab session:
python scripts/smoke_test_remote_dispatch.py
```

## FFmpeg

```bash
ffmpeg -i frames_%04d.png -i audio.wav -c:v h264_nvenc -c:a aac output.mp4
```

## Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Notes

Add commands here as they are validated against the real orchestrator and media engines.

## Related notes

- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/03 Hardware Constraints]]
