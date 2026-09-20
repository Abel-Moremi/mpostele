# Commands

This note holds the practical terminal commands used in the project.

## Ollama

```bash
ollama pull qwen2.5:1.5b
ollama serve
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:1.5b", "keep_alive": 0}'
```

## Remotion setup (one-time)

```bash
cd remotion && npm install
```

## Running a job

```bash
python -m app.main --media-type poster --brief-file examples/sample_brief.json
python -m app.main --media-type video --brief-file examples/sample_brief.json
```

## Rendering a composition directly (for debugging, without the Python orchestrator)

```bash
cd remotion
npx remotion still Poster out/test.png --props='{"headline":"...","ctaText":"...","backgroundColor":"#0B1220","accentColor":"#2563EB"}'
npx remotion render MainComposition out/test.mp4 --props='{"scenes":[...]}'
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
