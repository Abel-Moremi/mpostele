from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class Control:
    id: str
    role: str
    name: str
    tag: str
    href: str | None = None
    disabled: bool = False
    expanded: bool | None = None


@dataclass(frozen=True)
class Observation:
    url: str
    title: str
    headings: list[str]
    visible_text: str
    controls: list[Control]
    screenshot_path: str
    accessibility_path: str
    fingerprint: str


@dataclass(frozen=True)
class Analysis:
    summary: str
    purpose: str
    selected_action_ids: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TransitionResult:
    source_state_id: str
    action_id: str
    destination_state_id: str | None
    status: str
    observed_result: str


def as_record(value: Any) -> dict[str, Any]:
    return asdict(value)
