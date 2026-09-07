from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.request import Request, urlopen

from .models import SCHEMA_VERSION

CONTENT_PLAN_SCHEMA_VERSION = "1.0.0"
SUPPORTED_PLATFORMS = {"shorts", "reels", "tiktok", "landscape", "square"}


@dataclass(frozen=True)
class CampaignBrief:
    objective: str = "product overview"
    audience: str = "prospective users"
    platform: str = "shorts"
    target_duration_seconds: float = 30.0
    tone: str = "clear and practical"
    call_to_action: str = "Learn more"
    max_scenes: int = 6
    words_per_minute: int = 145

    def validated(self) -> "CampaignBrief":
        if not self.objective.strip() or not self.audience.strip() or not self.tone.strip():
            raise ValueError("objective, audience, and tone are required")
        if self.platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"platform must be one of: {', '.join(sorted(SUPPORTED_PLATFORMS))}")
        if not math.isfinite(self.target_duration_seconds) or not 5 <= self.target_duration_seconds <= 300:
            raise ValueError("target_duration_seconds must be between 5 and 300")
        if not 1 <= self.max_scenes <= 20:
            raise ValueError("max_scenes must be between 1 and 20")
        if not 80 <= self.words_per_minute <= 220:
            raise ValueError("words_per_minute must be between 80 and 220")
        return self


class ContentPlanningProvider(Protocol):
    name: str

    def propose(self, candidates: list[dict[str, Any]], brief: CampaignBrief) -> list[dict[str, Any]]: ...


def _clean(value: Any, limit: int = 180) -> str:
    return " ".join(str(value or "").split())[:limit]


@dataclass
class HeuristicContentPlanningProvider:
    name: str = "heuristic"

    def propose(self, candidates: list[dict[str, Any]], brief: CampaignBrief) -> list[dict[str, Any]]:
        selected = candidates[: brief.max_scenes]
        result = []
        for index, candidate in enumerate(selected):
            subject = candidate["purpose"] or candidate["heading"] or candidate["title"] or "the product"
            subject = subject.rstrip(".!?")
            narration = f"Take a closer look: {subject}." if index == 0 else f"Next: {subject}."
            if index == len(selected) - 1 and brief.call_to_action.strip():
                narration += f" {brief.call_to_action.strip().rstrip('.')}."
            result.append({
                "state_id": candidate["state_id"],
                "purpose": subject,
                "narration": narration,
                "overlay_text": candidate["heading"] or candidate["title"],
            })
        return result


@dataclass
class LlamaCppContentPlanningProvider:
    endpoint: str = "http://127.0.0.1:8080/v1/chat/completions"
    model: str = "qwen3-4b-instruct"
    timeout_seconds: float = 120.0
    name: str = "llama.cpp"

    def propose(self, candidates: list[dict[str, Any]], brief: CampaignBrief) -> list[dict[str, Any]]:
        evidence = [{
            "state_id": item["state_id"], "title": item["title"], "heading": item["heading"],
            "purpose": item["purpose"], "visible_text": item["visible_text"][:800],
            "transition_ids": item["transition_ids"], "important": item["important"],
        } for item in candidates]
        body = {
            "model": self.model, "temperature": 0.1, "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": (
                    "Create a concise product-video plan using only supplied evidence. Return JSON with a scenes array. "
                    "Each scene needs state_id, purpose, narration, and overlay_text. Use only supplied state IDs, "
                    "never invent claims, and keep narration within the duration budget."
                )},
                {"role": "user", "content": json.dumps({"brief": asdict(brief), "evidence": evidence}, ensure_ascii=False)},
            ],
        }
        request = Request(self.endpoint, data=json.dumps(body).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=self.timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        scenes = json.loads(result["choices"][0]["message"]["content"]).get("scenes", [])
        if not isinstance(scenes, list):
            raise ValueError("planning provider did not return a scenes array")
        return scenes


def load_discovery_snapshot(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"snapshot schema_version must be {SCHEMA_VERSION}")
    for key in ("pages", "states", "actions", "transitions", "findings"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"snapshot must contain a {key} array")
    return payload


def load_review(path: Path | str | None) -> dict[str, Any]:
    if not path:
        return {"actions": {}, "importantPages": [], "importantTransitions": []}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review must be a JSON object")
    actions = payload.get("actions", {})
    important_pages = payload.get("importantPages", [])
    important_transitions = payload.get("importantTransitions", [])
    if not isinstance(actions, dict) or any(value not in {"approved", "rejected"} for value in actions.values()):
        raise ValueError("review actions must contain approved or rejected decisions")
    if not isinstance(important_pages, list) or not all(isinstance(value, str) for value in important_pages):
        raise ValueError("review importantPages must be an array of IDs")
    if not isinstance(important_transitions, list) or not all(isinstance(value, str) for value in important_transitions):
        raise ValueError("review importantTransitions must be an array of IDs")
    return payload


def build_candidates(snapshot: dict[str, Any], review: dict[str, Any]) -> list[dict[str, Any]]:
    pages = {item["id"]: item for item in snapshot["pages"]}
    findings_by_state: dict[str, list[dict[str, Any]]] = {}
    for finding in snapshot["findings"]:
        if finding.get("state_id") and finding.get("status") != "rejected":
            findings_by_state.setdefault(finding["state_id"], []).append(finding)

    decisions = review.get("actions", {}) if isinstance(review.get("actions"), dict) else {}
    important_pages = set(review.get("importantPages", []))
    important_transitions = set(review.get("importantTransitions", []))
    transitions_by_state: dict[str, list[str]] = {}
    approved_by_state: dict[str, int] = {}
    for transition in snapshot["transitions"]:
        action_id = transition.get("action_id")
        if transition.get("status") != "verified" or decisions.get(action_id) == "rejected":
            continue
        transition_id = transition.get("id")
        for state_id in (transition.get("source_state_id"), transition.get("destination_state_id")):
            if state_id and transition_id:
                transitions_by_state.setdefault(state_id, []).append(transition_id)
                if decisions.get(action_id) == "approved":
                    approved_by_state[state_id] = approved_by_state.get(state_id, 0) + 1

    candidates = []
    for state in snapshot["states"]:
        observation = state.get("observation") or {}
        screenshot = _clean(observation.get("screenshot_path"), 500)
        if not screenshot:
            continue
        page = pages.get(state.get("page_id"), {})
        findings = findings_by_state.get(state["id"], [])
        purpose = next((item for item in findings if item.get("kind") == "page_purpose"), None)
        headings = observation.get("headings") if isinstance(observation.get("headings"), list) else []
        transition_ids = transitions_by_state.get(state["id"], [])
        important = state.get("page_id") in important_pages or any(item in important_transitions for item in transition_ids)
        score = (100 if important else 0) + (10 if transition_ids else 0) + (5 if findings else 0) + approved_by_state.get(state["id"], 0)
        candidates.append({
            "state_id": state["id"], "page_id": state.get("page_id"),
            "url": _clean(observation.get("url") or page.get("normalized_url"), 1000),
            "title": _clean(observation.get("title") or page.get("title")),
            "heading": _clean(headings[0] if headings else ""),
            "visible_text": _clean(observation.get("visible_text"), 2000),
            "screenshot_path": screenshot,
            "purpose": _clean(purpose.get("statement") if purpose else ""),
            "finding_ids": [item["id"] for item in findings if item.get("id")],
            "transition_ids": transition_ids, "important": important, "score": score,
        })
    return sorted(candidates, key=lambda item: (-item["score"], item["state_id"]))


def validate_and_expand_scenes(proposals: list[dict[str, Any]], candidates: list[dict[str, Any]],
                               brief: CampaignBrief) -> list[dict[str, Any]]:
    by_state = {item["state_id"]: item for item in candidates}
    scenes, used = [], set()
    word_budget = max(1, int(brief.target_duration_seconds * brief.words_per_minute / 60))
    used_words = 0
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        state_id = proposal.get("state_id")
        if state_id not in by_state or state_id in used or len(scenes) >= brief.max_scenes:
            continue
        candidate = by_state[state_id]
        narration = _clean(proposal.get("narration"), 500)
        words = len(narration.split())
        if not narration or used_words + words > word_budget:
            continue
        scenes.append({
            "id": f"scene-{len(scenes) + 1:02d}",
            "purpose": _clean(proposal.get("purpose")) or candidate["purpose"] or candidate["heading"],
            "evidence": {
                "page_id": candidate["page_id"], "state_id": state_id,
                "finding_ids": candidate["finding_ids"], "transition_ids": candidate["transition_ids"],
                "screenshot_path": candidate["screenshot_path"],
            },
            "capture": {"type": "state", "url": candidate["url"]},
            "narration": narration,
            "overlay": {"type": "title", "text": _clean(proposal.get("overlay_text"), 80) or candidate["heading"]},
            "estimated_duration_seconds": round(max(2.5, words / brief.words_per_minute * 60 + 0.5), 2),
            "confidence": 0.9 if candidate["important"] else 0.7,
            "review_status": "pending",
        })
        used.add(state_id)
        used_words += words
    if not scenes:
        raise ValueError("no valid evidence-backed scenes were produced")
    return scenes


def generate_content_plan(snapshot_path: Path | str, output_path: Path | str, brief: CampaignBrief,
                          provider: ContentPlanningProvider, review_path: Path | str | None = None) -> Path:
    brief = brief.validated()
    snapshot = load_discovery_snapshot(snapshot_path)
    candidates = build_candidates(snapshot, load_review(review_path))
    if not candidates:
        raise ValueError("snapshot contains no screenshot-backed states")
    planning_candidates = candidates[:min(40, max(12, brief.max_scenes * 4))]
    try:
        proposals = provider.propose(planning_candidates, brief)
        scenes = validate_and_expand_scenes(proposals, planning_candidates, brief)
        producer = provider.name
    except Exception:
        if provider.name == "heuristic":
            raise
        fallback = HeuristicContentPlanningProvider()
        proposals = fallback.propose(planning_candidates, brief)
        scenes = validate_and_expand_scenes(proposals, planning_candidates, brief)
        producer = fallback.name
    target = Path(output_path)
    if target.resolve() == Path(snapshot_path).resolve() or (review_path and target.resolve() == Path(review_path).resolve()):
        raise ValueError("output must not overwrite the snapshot or review file")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CONTENT_PLAN_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(), "producer": producer,
        "source": {"snapshot": str(Path(snapshot_path)), "review": str(Path(review_path)) if review_path else None,
                   "discovery_schema_version": snapshot["schema_version"]},
        "brief": asdict(brief), "status": "pending_review", "scenes": scenes,
    }
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an evidence-backed local content plan.")
    parser.add_argument("snapshot", help="Discovery snapshot.json path")
    parser.add_argument("--review", help="Optional review.json path")
    parser.add_argument("--output", default="content-plan.json", help="Output JSON path")
    parser.add_argument("--objective", default="product overview")
    parser.add_argument("--audience", default="prospective users")
    parser.add_argument("--platform", choices=sorted(SUPPORTED_PLATFORMS), default="shorts")
    parser.add_argument("--duration", type=float, default=30.0, help="Target duration in seconds")
    parser.add_argument("--tone", default="clear and practical")
    parser.add_argument("--call-to-action", default="Learn more")
    parser.add_argument("--max-scenes", type=int, default=6)
    parser.add_argument("--words-per-minute", type=int, default=145)
    parser.add_argument("--provider", choices=("heuristic", "llama.cpp"), default="heuristic")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model", default="qwen3-4b-instruct")
    args = parser.parse_args()
    brief = CampaignBrief(args.objective, args.audience, args.platform, args.duration, args.tone,
                          args.call_to_action, args.max_scenes, args.words_per_minute)
    provider: ContentPlanningProvider = (HeuristicContentPlanningProvider() if args.provider == "heuristic"
        else LlamaCppContentPlanningProvider(args.endpoint, args.model))
    result = generate_content_plan(args.snapshot, args.output, brief, provider, args.review)
    print(f"Content plan ready for review: {result}")


if __name__ == "__main__":
    main()
