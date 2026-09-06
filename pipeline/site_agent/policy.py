from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from .models import Control


BLOCKED_ACTION_PATTERN = re.compile(
    r"\b(delete|remove|destroy|purchase|buy|pay|subscribe|publish|send|invite|"
    r"disconnect|revoke|reset|logout|log out|sign out|checkout|confirm order)\b",
    re.IGNORECASE,
)
SAFE_ROLES = {"link", "tab", "button"}
TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


def normalize_url(url: str, base_url: str | None = None) -> str:
    absolute = urljoin(base_url or url, url)
    parts = urlsplit(absolute)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), "")
    )


def is_allowed_url(url: str, allowed_domains: tuple[str, ...]) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def classify_control(control: Control, allowed_domains: tuple[str, ...]) -> tuple[str, str]:
    label = f"{control.name} {control.href or ''}".strip()
    if control.disabled:
        return "blocked", "control is disabled"
    if BLOCKED_ACTION_PATTERN.search(label):
        return "blocked", "label indicates a destructive or consequential action"
    if control.role not in SAFE_ROLES:
        return "blocked", f"role {control.role!r} is outside the safe interaction allowlist"
    if control.href:
        if control.href.startswith(("mailto:", "tel:", "javascript:")):
            return "blocked", "non-navigation link scheme"
        if not is_allowed_url(control.href, allowed_domains):
            return "blocked", "destination is outside the allowed domains"
    if control.role == "button" and control.expanded is None and not re.search(
        r"\b(open|close|menu|more|details|learn|view|show|hide|next|previous|back)\b",
        control.name,
        re.IGNORECASE,
    ):
        return "review", "button is not known to be a reversible disclosure action"
    return "safe", "allowed reversible navigation or disclosure action"
