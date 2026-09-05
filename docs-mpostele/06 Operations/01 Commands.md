# Commands

This note should hold the practical terminal commands used in the project.

## FFmpeg examples

```bash
ffmpeg -i input.mp4 -vf "zoompan" output.mp4
ffmpeg -i video.mp4 -i audio.wav -c:v h264_nvenc -c:a aac output.mp4
```

## Playwright

```bash
npx playwright install
npx playwright test
```

## Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Notes

Add commands here as they are validated in the real workflow.

## Related notes

- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/03 Hardware Constraints]]
