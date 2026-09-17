"""Spawns each pipeline stage as its own OS-level subprocess.

Process exit reclaims that stage's VRAM/RAM regardless of whether an
in-process flush ran - this is the outer guarantee the explicit unload
hooks in app/media/memory.py layer on top of.
"""
import subprocess
import sys


def run_stage(module: str, job_id: str, *, check_exit_code: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", module, "--job", job_id],
        check=check_exit_code,
    )
