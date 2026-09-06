from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .models import Control, Observation
from .policy import normalize_url


CONTROL_SELECTOR = "a, button, summary, [role='link'], [role='button'], [role='tab']"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return cleaned[:50] or "state"


def observe_page(page: Any, output_dir: Path | str, sequence: int) -> Observation:
    """Capture a compact semantic observation and human-reviewable evidence."""
    extracted = page.evaluate(
        """
        (selector) => {
          const visible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
          };
          const controls = Array.from(document.querySelectorAll(selector))
            .filter(visible)
            .slice(0, 200)
            .map((element, index) => {
              const id = `control-${index}`;
              element.setAttribute('data-mpostele-action-id', id);
              const tag = element.tagName.toLowerCase();
              const role = element.getAttribute('role') || (tag === 'a' ? 'link' : tag === 'summary' ? 'button' : 'button');
              const name = (element.getAttribute('aria-label') || element.innerText || element.getAttribute('title') || '').trim().replace(/\\s+/g, ' ').slice(0, 200);
              const expanded = element.getAttribute('aria-expanded');
              return {
                id, role, name, tag,
                href: tag === 'a' ? element.href : null,
                disabled: Boolean(element.disabled) || element.getAttribute('aria-disabled') === 'true',
                expanded: expanded === null ? null : expanded === 'true'
              };
            });
          const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
            .filter(visible).map((item) => item.innerText.trim().replace(/\\s+/g, ' ')).filter(Boolean).slice(0, 80);
          return {
            title: document.title,
            headings,
            visibleText: (document.body?.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 20000),
            controls
          };
        }
        """,
        CONTROL_SELECTOR,
    )
    url = normalize_url(page.url)
    controls = [Control(**item) for item in extracted["controls"]]
    fingerprint_input = {
        "url": url,
        "title": extracted["title"],
        "headings": extracted["headings"],
        "text": extracted["visibleText"][:10000],
        "controls": [(item.role, item.name, item.href, item.expanded) for item in controls],
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_input, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    evidence_name = f"{sequence:04d}-{_slug(extracted['title'])}-{fingerprint[:10]}"
    root = Path(output_dir)
    screenshot_path = root / "screenshots" / f"{evidence_name}.png"
    accessibility_path = root / "accessibility" / f"{evidence_name}.txt"
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    accessibility_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(screenshot_path), full_page=False)
    try:
        accessibility = page.locator("body").aria_snapshot(timeout=5000)
    except Exception:
        accessibility = extracted["visibleText"]
    accessibility_path.write_text(accessibility, encoding="utf-8")
    return Observation(
        url=url,
        title=extracted["title"],
        headings=extracted["headings"],
        visible_text=extracted["visibleText"],
        controls=controls,
        screenshot_path=screenshot_path.relative_to(root).as_posix(),
        accessibility_path=accessibility_path.relative_to(root).as_posix(),
        fingerprint=fingerprint,
    )


def tag_controls(page: Any) -> None:
    """Restore deterministic action IDs after reloading a previously observed page."""
    page.evaluate(
        """
        (selector) => {
          const visible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
          };
          Array.from(document.querySelectorAll(selector)).filter(visible).slice(0, 200)
            .forEach((element, index) => element.setAttribute('data-mpostele-action-id', `control-${index}`));
        }
        """,
        CONTROL_SELECTOR,
    )


def click_control(page: Any, control_id: str, timeout_ms: int = 10000) -> None:
    locator = page.locator(f'[data-mpostele-action-id="{control_id}"]').first
    locator.click(timeout=timeout_ms)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(500)
