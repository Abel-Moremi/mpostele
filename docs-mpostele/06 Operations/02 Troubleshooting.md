# Troubleshooting

## Common issues

### Audio sync problems

- verify audio duration relative to video timeline
- trim voiceover to match the final sequence length
- double-check frame rate consistency

### Video quality issues

- ensure output resolution matches intended export dimensions
- test NVENC acceleration support before relying on it
- simplify animations if the system is under load

### Resource limits

- reduce animation complexity
- generate shorter scenes
- prefer FFmpeg or pre-rendered overlays over heavy live generation

### Login capture failures

- `CaptureError: ... no password field was found` — the target page (and a click on any 'Log in'/'Sign in' entry point) still doesn't expose a recognizable login form; check the URL/target-path or capture without credentials
- `LoginVerificationError: ... appears to have failed` — an element matching an error-message selector (`[role='alert']`, `.error`, etc.) also contained error-like wording (e.g. "invalid", "incorrect", "failed"). Only elements whose text looks like an actual error count as a failure — for example, some frameworks (Nuxt/Vue) insert an accessibility "route announcer" with `role="alert"` that just echoes the current page title on every navigation; that text is ignored since it doesn't match error wording. If a real error report still misfires, check the exact message in the exception — it may need an additional keyword or selector.
- `LoginVerificationError: Timed out waiting to verify` — the URL didn't change and the password field is still visible after the timeout; the site may use unrecognized field/button selectors or a slower redirect than expected

## Related notes

- [[06 Operations/01 Commands]]
- [[06 Operations/03 Hardware Constraints]]
