# Commands

This note holds the practical terminal commands used in the project.

## Ollama

```bash
ollama pull qwen2.5:1.5b
ollama serve
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:1.5b", "keep_alive": 0}'
```

## Revideo setup (one-time)

```bash
cd revideo && npm install
```

## Running a job

```bash
python -m app.main --media-type poster --brief-file examples/sample_brief.json
python -m app.main --media-type video --brief-file examples/sample_brief.json
```

## Rendering a composition directly (for debugging, without the Python orchestrator)

```bash
cd revideo
node render.mjs --project poster --props poster_props.json --out out/test.png
node render.mjs --project video --props composition_props.json --out out/test.mp4
```

## FFmpeg

```bash
ffmpeg -i raw_clip.mp4 -c:v libx264 -c:a aac output.mp4
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
