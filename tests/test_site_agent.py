import json
import tempfile
import unittest
from pathlib import Path

from pipeline.site_agent.agent import AgentConfig, stable_id
from pipeline.site_agent.models import Analysis, Control, Observation, SCHEMA_VERSION, as_record
from pipeline.site_agent.policy import classify_control, is_allowed_url, normalize_url
from pipeline.site_agent.reasoning import HeuristicProvider
from pipeline.site_agent.store import KnowledgeStore


class SiteAgentPolicyTests(unittest.TestCase):
    def test_normalize_url_removes_fragment_tracking_and_trailing_slash(self):
        result = normalize_url("HTTPS://Example.COM/docs/?utm_source=test&b=2&a=1#intro")
        self.assertEqual(result, "https://example.com/docs?a=1&b=2")

    def test_domain_policy_allows_subdomains_but_not_suffix_attacks(self):
        self.assertTrue(is_allowed_url("https://app.example.com/home", ("example.com",)))
        self.assertFalse(is_allowed_url("https://example.com.attacker.test", ("example.com",)))

    def test_policy_blocks_consequential_controls(self):
        control = Control("control-0", "button", "Delete account", "button")
        safety, reason = classify_control(control, ("example.com",))
        self.assertEqual(safety, "blocked")
        self.assertIn("destructive", reason)

    def test_policy_marks_unknown_buttons_for_review(self):
        control = Control("control-0", "button", "Generate report", "button")
        safety, _ = classify_control(control, ("example.com",))
        self.assertEqual(safety, "review")

    def test_policy_allows_reversible_expansion(self):
        control = Control("control-0", "button", "Advanced settings", "button", expanded=False)
        safety, _ = classify_control(control, ("example.com",))
        self.assertEqual(safety, "safe")


class SiteAgentStoreTests(unittest.TestCase):
    def test_store_exports_evidence_and_inference_separately(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observation = Observation(
                url="https://example.com/",
                title="Example",
                headings=["Welcome"],
                visible_text="Welcome to Example",
                controls=[Control("control-0", "link", "Docs", "a", "https://example.com/docs")],
                screenshot_path="screenshots/example.png",
                accessibility_path="accessibility/example.txt",
                fingerprint="fingerprint",
            )
            analysis = Analysis("Landing page", "Introduce the product", ["control-0"])
            page_id = stable_id("page", observation.url)
            state_id = stable_id("state", page_id, observation.fingerprint)
            action_id = stable_id("action", state_id, "control-0")

            with KnowledgeStore(root / "knowledge.sqlite") as store:
                store.start_run("run_test", {"start_url": observation.url})
                inserted = store.save_state(
                    page_id,
                    state_id,
                    observation,
                    analysis,
                    [(action_id, as_record(observation.controls[0]), "safe", "internal link")],
                )
                store.save_event(
                    "event_test",
                    "run_test",
                    "navigation",
                    "https://example.com/missing",
                    "failed",
                    "Timed out",
                )
                store.save_finding(
                    "finding_test",
                    state_id,
                    "page_purpose",
                    analysis.purpose,
                    "inferred",
                    0.7,
                    [state_id],
                    "test-provider",
                )
                store.complete_run("run_test")
                snapshot_path = store.export_snapshot(root / "snapshot.json")

            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.assertTrue(inserted)
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
            self.assertEqual(payload["states"][0]["observation"]["title"], "Example")
            self.assertEqual(payload["findings"][0]["status"], "inferred")
            self.assertEqual(payload["findings"][0]["evidence"], [state_id])
            self.assertEqual(payload["events"][0]["status"], "failed")

    def test_heuristic_provider_only_selects_supplied_safe_actions(self):
        observation = Observation(
            url="https://example.com/",
            title="Example",
            headings=[],
            visible_text="",
            controls=[],
            screenshot_path="",
            accessibility_path="",
            fingerprint="fingerprint",
        )
        analysis = HeuristicProvider().analyze(observation, ["safe-1", "safe-2"])
        self.assertEqual(analysis.selected_action_ids, ["safe-1", "safe-2"])


class SiteAgentConfigTests(unittest.TestCase):
    def test_config_derives_allowed_domain(self):
        config = AgentConfig("https://App.Example.com/start").validated()
        self.assertEqual(config.allowed_domains, ("app.example.com",))

    def test_config_rejects_non_http_url(self):
        with self.assertRaises(ValueError):
            AgentConfig("file:///tmp/site.html").validated()

    def test_config_requires_start_url_to_be_allowed(self):
        with self.assertRaises(ValueError):
            AgentConfig("https://example.com", allowed_domains=("other.test",)).validated()


if __name__ == "__main__":
    unittest.main()
