from __future__ import annotations

import hashlib
import json
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .browser import click_control, observe_page, tag_controls
from .models import Analysis, Observation, as_record
from .policy import classify_control, is_allowed_url, normalize_url
from .reasoning import HeuristicProvider, ReasoningProvider
from .store import KnowledgeStore


@dataclass(frozen=True)
class AgentConfig:
    start_url: str
    output_dir: str = "artifacts/site-analysis/latest"
    allowed_domains: tuple[str, ...] = ()
    max_pages: int = 30
    max_interactions: int = 20
    max_depth: int = 4
    width: int = 1280
    height: int = 720
    storage_state: str = ""
    headless: bool = True

    def validated(self) -> "AgentConfig":
        parsed = urlsplit(self.start_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("start_url must be an absolute http(s) URL")
        if self.max_pages < 1 or self.max_interactions < 0 or self.max_depth < 0:
            raise ValueError("crawl limits must be non-negative and max_pages must be at least 1")
        domains = tuple(item.lower() for item in (self.allowed_domains or (parsed.hostname.lower(),)))
        if not is_allowed_url(self.start_url, domains):
            raise ValueError("start_url must belong to one of allowed_domains")
        return AgentConfig(**{**asdict(self), "allowed_domains": domains})


@dataclass(frozen=True)
class PendingPage:
    url: str
    depth: int
    source_state_id: str | None = None
    action_id: str | None = None


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


class SiteDiscoveryAgent:
    def __init__(self, config: AgentConfig, provider: ReasoningProvider):
        self.config = config.validated()
        self.provider = provider
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.decision_log = self.output_dir / "decisions.jsonl"
        self.sequence = 0

    def _record_decision(self, payload: dict[str, Any]) -> None:
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
        with self.decision_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _analyze(self, observation: Observation, safe_ids: list[str]) -> tuple[Analysis, str]:
        try:
            analysis = self.provider.analyze(observation, safe_ids)
            self._record_decision(
                {
                    "event": "analysis",
                    "provider": self.provider.name,
                    "url": observation.url,
                    "selected_action_ids": analysis.selected_action_ids,
                }
            )
            return analysis, self.provider.name
        except Exception as error:
            self._record_decision(
                {
                    "event": "provider_error",
                    "provider": self.provider.name,
                    "url": observation.url,
                    "error": str(error),
                    "fallback": "heuristic",
                }
            )
            fallback = HeuristicProvider()
            return fallback.analyze(observation, safe_ids), fallback.name

    def _save_observation(
        self, store: KnowledgeStore, observation: Observation
    ) -> tuple[str, Analysis, dict[str, tuple[str, str, str]]]:
        page_id = stable_id("page", observation.url)
        state_id = stable_id("state", page_id, observation.fingerprint)
        classifications: dict[str, tuple[str, str, str]] = {}
        action_rows = []
        safe_ids = []
        for control in observation.controls:
            safety, reason = classify_control(control, self.config.allowed_domains)
            action_id = stable_id("action", state_id, control.id, control.role, control.name, control.href or "")
            classifications[control.id] = (action_id, safety, reason)
            action_rows.append((action_id, as_record(control), safety, reason))
            if safety == "safe":
                safe_ids.append(control.id)
        analysis, producer = self._analyze(observation, safe_ids)
        store.save_state(page_id, state_id, observation, analysis, action_rows)
        store.save_finding(
            stable_id("finding", state_id, "purpose", analysis.purpose),
            state_id,
            "page_purpose",
            analysis.purpose,
            "inferred",
            0.7,
            [state_id],
            producer,
        )
        for index, finding in enumerate(analysis.findings):
            store.save_finding(
                stable_id("finding", state_id, str(index), finding["statement"]),
                state_id,
                finding.get("kind", "page_interpretation"),
                finding["statement"],
                "inferred",
                float(finding.get("confidence", 0.5)),
                [state_id],
                producer,
            )
        return state_id, analysis, classifications

    def _observe(self, page: Any) -> Observation:
        self.sequence += 1
        return observe_page(page, self.output_dir, self.sequence)

    def run(self) -> Path:
        from playwright.sync_api import sync_playwright

        run_id = f"run_{uuid.uuid4().hex}"
        manifest = {**asdict(self.config), "provider": self.provider.name, "run_id": run_id}
        (self.output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        store = KnowledgeStore(self.output_dir / "knowledge.sqlite")
        store.start_run(run_id, manifest)
        queue = deque([PendingPage(normalize_url(self.config.start_url), 0)])
        queued = {normalize_url(self.config.start_url)}
        visited: dict[str, str] = {}
        interactions = 0
        navigation_failures = 0
        status = "completed"

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.config.headless)
                context_args: dict[str, Any] = {
                    "viewport": {"width": self.config.width, "height": self.config.height}
                }
                if self.config.storage_state:
                    context_args["storage_state"] = self.config.storage_state
                context = browser.new_context(**context_args)
                page = context.new_page()
                try:
                    while queue and len(visited) < self.config.max_pages:
                        pending = queue.popleft()
                        normalized = normalize_url(pending.url)
                        if normalized in visited:
                            if pending.source_state_id and pending.action_id:
                                store.save_transition(
                                    stable_id("transition", pending.source_state_id, pending.action_id, visited[normalized]),
                                    pending.source_state_id,
                                    pending.action_id,
                                    visited[normalized],
                                    "verified",
                                    f"Navigated to previously observed page {normalized}",
                                )
                            continue
                        if not is_allowed_url(normalized, self.config.allowed_domains):
                            continue
                        try:
                            page.goto(normalized, wait_until="domcontentloaded", timeout=60000)
                            try:
                                page.wait_for_load_state("networkidle", timeout=5000)
                            except Exception:
                                pass
                            observation = self._observe(page)
                        except Exception as error:
                            navigation_failures += 1
                            self._record_decision({"event": "navigation_error", "url": normalized, "error": str(error)})
                            store.save_event(
                                stable_id("event", run_id, "navigation_error", normalized),
                                run_id,
                                "navigation",
                                normalized,
                                "failed",
                                str(error),
                            )
                            continue
                        if not is_allowed_url(observation.url, self.config.allowed_domains):
                            store.save_event(
                                stable_id("event", run_id, "external_redirect", observation.url),
                                run_id,
                                "redirect",
                                observation.url,
                                "blocked",
                                f"Navigation left allowed domains from {normalized}",
                            )
                            continue
                        state_id, analysis, classifications = self._save_observation(store, observation)
                        visited[observation.url] = state_id
                        if pending.source_state_id and pending.action_id:
                            store.save_transition(
                                stable_id("transition", pending.source_state_id, pending.action_id, state_id),
                                pending.source_state_id,
                                pending.action_id,
                                state_id,
                                "verified",
                                f"Navigation reached {observation.url}",
                            )

                        if pending.depth < self.config.max_depth:
                            for control in observation.controls:
                                action_id, safety, _ = classifications[control.id]
                                if safety != "safe" or not control.href:
                                    continue
                                target = normalize_url(control.href, observation.url)
                                if target not in queued and is_allowed_url(target, self.config.allowed_domains):
                                    queue.append(PendingPage(target, pending.depth + 1, state_id, action_id))
                                    queued.add(target)

                        selected = set(analysis.selected_action_ids)
                        interactive = [
                            control for control in observation.controls
                            if control.id in selected
                            and not control.href
                            and classifications[control.id][1] == "safe"
                        ]
                        for control in interactive:
                            if interactions >= self.config.max_interactions:
                                break
                            page.goto(observation.url, wait_until="domcontentloaded", timeout=60000)
                            page.wait_for_timeout(250)
                            tag_controls(page)
                            action_id = classifications[control.id][0]
                            interactions += 1
                            try:
                                click_control(page, control.id)
                                destination = self._observe(page)
                                if not is_allowed_url(destination.url, self.config.allowed_domains):
                                    store.save_transition(
                                        stable_id("transition", state_id, action_id, "external"),
                                        state_id,
                                        action_id,
                                        None,
                                        "blocked",
                                        f"Interaction left the allowed domains for {destination.url}",
                                    )
                                    continue
                                destination_state_id, _, _ = self._save_observation(store, destination)
                                changed = destination.fingerprint != observation.fingerprint
                                store.save_transition(
                                    stable_id("transition", state_id, action_id, destination_state_id),
                                    state_id,
                                    action_id,
                                    destination_state_id,
                                    "verified" if changed else "no_change",
                                    "UI state changed" if changed else "No observable state change",
                                )
                            except Exception as error:
                                store.save_transition(
                                    stable_id("transition", state_id, action_id, "failed"),
                                    state_id,
                                    action_id,
                                    None,
                                    "failed",
                                    str(error),
                                )
                            finally:
                                try:
                                    page.goto(observation.url, wait_until="domcontentloaded", timeout=60000)
                                    page.wait_for_timeout(250)
                                except Exception as error:
                                    self._record_decision(
                                        {"event": "state_reset_error", "url": observation.url, "error": str(error)}
                                    )
                finally:
                    context.close()
                    browser.close()
            if navigation_failures:
                status = "partial"
        except Exception:
            status = "failed"
            raise
        finally:
            store.complete_run(run_id, status)
            snapshot = store.export_snapshot(self.output_dir / "snapshot.json")
            self._write_coverage(store)
            store.close()
        return snapshot

    def _write_coverage(self, store: KnowledgeStore) -> None:
        coverage = store.coverage()
        lines = [
            "# Site Discovery Coverage",
            "",
            f"- Pages: {coverage['pages']}",
            f"- UI states: {coverage['states']}",
            f"- Controls: {coverage['actions']}",
            f"- Verified or attempted transitions: {coverage['transitions']}",
            f"- Inferred findings: {coverage['findings']}",
            f"- Run events: {coverage['events']}",
            f"- Failed events: {coverage['failed_events']}",
            f"- Blocked controls: {coverage['blocked_actions']}",
            f"- Unexplored controls: {coverage['unexplored_actions']}",
            "",
            "Unexplored and blocked controls remain explicit; this report does not claim complete coverage.",
        ]
        reports = self.output_dir / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
