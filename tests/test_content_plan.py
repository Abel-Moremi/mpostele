import json
import tempfile
import unittest
from pathlib import Path

from pipeline.site_agent.content_plan import (
    CONTENT_PLAN_SCHEMA_VERSION,
    CampaignBrief,
    HeuristicContentPlanningProvider,
    build_candidates,
    generate_content_plan,
)
from pipeline.site_agent.models import SCHEMA_VERSION


def snapshot_fixture():
    return {
        "schema_version": SCHEMA_VERSION,
        "pages": [
            {"id": "page-home", "normalized_url": "https://example.com", "title": "Home"},
            {"id": "page-calendar", "normalized_url": "https://example.com/calendar", "title": "Calendar"},
        ],
        "states": [
            {"id": "state-home", "page_id": "page-home", "observation": {
                "url": "https://example.com", "title": "Home", "headings": ["Plan campaigns"],
                "visible_text": "Plan and publish campaigns.", "screenshot_path": "screenshots/home.png",
            }},
            {"id": "state-calendar", "page_id": "page-calendar", "observation": {
                "url": "https://example.com/calendar", "title": "Calendar", "headings": ["Content calendar"],
                "visible_text": "Schedule campaign content.", "screenshot_path": "screenshots/calendar.png",
            }},
        ],
        "actions": [{"id": "action-open", "state_id": "state-home", "safety": "safe"}],
        "transitions": [{
            "id": "transition-open", "source_state_id": "state-home", "action_id": "action-open",
            "destination_state_id": "state-calendar", "status": "verified",
        }],
        "findings": [{
            "id": "finding-calendar", "state_id": "state-calendar", "kind": "page_purpose",
            "statement": "Schedule content", "status": "inferred", "confidence": 0.8,
        }],
    }


class InvalidProvider:
    name = "llama.cpp"

    def propose(self, candidates, brief):
        return [{"state_id": "invented", "narration": "Unsupported scene"}]


class ContentPlanTests(unittest.TestCase):
    def test_review_markers_prioritize_evidence_and_rejections_remove_transition(self):
        snapshot = snapshot_fixture()
        candidates = build_candidates(snapshot, {
            "actions": {"action-open": "rejected"},
            "importantPages": ["page-calendar"],
            "importantTransitions": ["transition-open"],
        })
        self.assertEqual(candidates[0]["state_id"], "state-calendar")
        self.assertTrue(candidates[0]["important"])
        self.assertEqual(candidates[0]["transition_ids"], [])

    def test_generates_versioned_evidence_backed_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot_path = root / "snapshot.json"
            review_path = root / "review.json"
            output_path = root / "content-plan.json"
            snapshot_path.write_text(json.dumps(snapshot_fixture()), encoding="utf-8")
            review_path.write_text(json.dumps({
                "actions": {}, "importantPages": ["page-calendar"], "importantTransitions": []
            }), encoding="utf-8")

            generate_content_plan(
                snapshot_path, output_path,
                CampaignBrief(target_duration_seconds=20, max_scenes=2),
                HeuristicContentPlanningProvider(), review_path,
            )
            plan = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(plan["schema_version"], CONTENT_PLAN_SCHEMA_VERSION)
            self.assertEqual(plan["status"], "pending_review")
            self.assertEqual(plan["scenes"][0]["evidence"]["state_id"], "state-calendar")
            self.assertEqual(plan["scenes"][0]["review_status"], "pending")
            self.assertTrue(plan["scenes"][0]["evidence"]["screenshot_path"])

    def test_invalid_model_plan_falls_back_to_heuristic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot_path = root / "snapshot.json"
            output_path = root / "content-plan.json"
            snapshot_path.write_text(json.dumps(snapshot_fixture()), encoding="utf-8")

            generate_content_plan(snapshot_path, output_path, CampaignBrief(), InvalidProvider())
            plan = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(plan["producer"], "heuristic")
            self.assertNotEqual(plan["scenes"][0]["evidence"]["state_id"], "invented")

    def test_rejects_snapshot_without_screenshot_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = snapshot_fixture()
            for state in snapshot["states"]:
                state["observation"]["screenshot_path"] = ""
            snapshot_path = root / "snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "screenshot-backed"):
                generate_content_plan(
                    snapshot_path, root / "plan.json", CampaignBrief(),
                    HeuristicContentPlanningProvider(),
                )

    def test_validates_duration_and_scene_limits(self):
        with self.assertRaises(ValueError):
            CampaignBrief(target_duration_seconds=2).validated()
        with self.assertRaises(ValueError):
            CampaignBrief(max_scenes=21).validated()


if __name__ == "__main__":
    unittest.main()
