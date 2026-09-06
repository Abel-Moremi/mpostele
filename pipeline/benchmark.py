"""Measure render wall time and peak process-tree working memory.

The sampler uses only the Python standard library. On Windows it reads process
information through Win32 APIs; on Linux it reads /proc. No monitoring service
or persistent background process is required.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class BenchmarkResult:
    command: tuple[str, ...]
    elapsed_seconds: float
    peak_tree_rss_bytes: int | None
    samples: int
    exit_code: int

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["command"] = list(self.command)
        data["peak_tree_rss_mib"] = (
            round(self.peak_tree_rss_bytes / (1024 * 1024), 2)
            if self.peak_tree_rss_bytes is not None
            else None
        )
        return data


def _descendants(root_pid: int, parent_by_pid: dict[int, int]) -> set[int]:
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parent_by_pid.items():
            if parent in selected and pid not in selected:
                selected.add(pid)
                changed = True
    return selected


def _linux_process_tree_rss(root_pid: int) -> int | None:
    process_dir = Path("/proc")
    parents: dict[int, int] = {}
    for entry in process_dir.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="utf-8").split()
            parents[int(entry.name)] = int(fields[3])
        except (OSError, ValueError, IndexError):
            continue
    total = 0
    found = False
    page_size = os.sysconf("SC_PAGE_SIZE")
    for pid in _descendants(root_pid, parents):
        try:
            resident_pages = int(
                (process_dir / str(pid) / "statm").read_text(encoding="utf-8").split()[1]
            )
        except (OSError, ValueError, IndexError):
            continue
        total += resident_pages * page_size
        found = True
    return total if found else None


def _windows_process_tree_rss(root_pid: int) -> int | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    max_path = 260

    class ProcessEntry32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * max_path),
        ]

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        return None
    parents: dict[int, int] = {}
    entry = ProcessEntry32()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        success = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while success:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            success = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    total = 0
    found = False
    for pid in _descendants(root_pid, parents):
        handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
        if not handle:
            continue
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        try:
            if psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), ctypes.sizeof(counters)
            ):
                total += int(counters.WorkingSetSize)
                found = True
        finally:
            kernel32.CloseHandle(handle)
    return total if found else None


def process_tree_rss(root_pid: int) -> int | None:
    """Return aggregate resident/working-set bytes for a process and children."""
    if sys.platform == "win32":
        return _windows_process_tree_rss(root_pid)
    if sys.platform.startswith("linux"):
        return _linux_process_tree_rss(root_pid)
    return None


def run_benchmark(
    command: Sequence[str],
    *,
    sample_interval: float = 0.1,
    sampler: Callable[[int], int | None] = process_tree_rss,
) -> BenchmarkResult:
    """Run a command without a shell and measure its process tree."""
    if not command:
        raise ValueError("Benchmark command must not be empty")
    if sample_interval <= 0:
        raise ValueError("Sample interval must be greater than zero")

    started = time.perf_counter()
    process = subprocess.Popen(list(command))
    peak: int | None = None
    samples = 0
    while True:
        current = sampler(process.pid)
        if current is not None:
            peak = max(peak or 0, current)
        samples += 1
        try:
            process.wait(timeout=sample_interval)
        except subprocess.TimeoutExpired:
            continue
        break
    elapsed = time.perf_counter() - started
    return BenchmarkResult(
        command=tuple(command),
        elapsed_seconds=round(elapsed, 3),
        peak_tree_rss_bytes=peak,
        samples=samples,
        exit_code=int(process.returncode),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark a local command's wall time and process-tree memory."
    )
    parser.add_argument("--report", help="Optional JSON report path")
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=0.1,
        help="Memory sample interval in seconds (default: 0.1)",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide a command after --")
    try:
        result = run_benchmark(command, sample_interval=args.sample_interval)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    report = result.to_dict()
    payload = json.dumps(report, indent=2)
    print(payload)
    if args.report:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
    if result.exit_code:
        raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
