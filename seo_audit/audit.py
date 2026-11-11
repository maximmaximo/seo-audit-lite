"""Bounded, SSRF-aware HTML fetching and transparent on-page SEO checks."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
import requests

MAX_BYTES = 2_000_000
TIMEOUT = (4, 9)
MAX_REDIRECTS = 4
USER_AGENT = "SEOAuditLite/1.0 (+public on-page SEO inspection)"


class AuditError(Exception):
    """User-friendly fetch or parsing failure."""


@dataclass
class Check:
    category: str
    name: str
    status: str
    detail: str
    recommendation: str
    points: int
    max_points: int = 10


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise AuditError("Enter a website URL to begin.")
    if "://" in value and not re.match(r"^https?://", value, re.I):
        raise AuditError("Only HTTP and HTTPS URLs are supported.")
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise AuditError("Only valid HTTP and HTTPS website URLs are supported.")
    if parts.username or parts.password:
        raise AuditError("URLs containing credentials are not supported.")
    try:
        port = parts.port
    except ValueError as exc:
        raise AuditError("Invalid URL port.") from exc
    if port not in (None, 80, 443):
        raise AuditError("Only standard HTTP/HTTPS ports are supported.")
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def validate_public_url(url: str) -> None:
    parts = urlsplit(url)
    hostname = parts.hostname
    if not hostname:
        raise AuditError("The URL has no hostname.")
    if hostname.lower() in {"localhost", "localhost.localdomain"} or hostname.lower().endswith((".local", ".internal", ".localhost")):
        raise AuditError("Private or local hostnames cannot be scanned.")
    try:
        records = socket.getaddrinfo(hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise AuditError("The hostname could not be resolved.") from exc
    if not records:
        raise AuditError("The hostname has no DNS records.")
    for record in records:
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise AuditError("Private, reserved, or local IP addresses cannot be scanned.")


def fetch_html(value: str) -> tuple[str, str, dict]:
    """Fetch a small public HTML page; disable proxies and auto redirects.

    DNS is checked before each request. For hardened multi-tenant deployments,
    additionally enforce outbound network restrictions to prevent DNS rebinding.
    """
    url = normalize_url(value)
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        for _ in range(MAX_REDIRECTS + 1):
            validate_public_url(url)
            try:
                with session.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        target = response.headers.get("Location")
                        if not target:
                            raise AuditError("The website returned a redirect without a destination.")
                        url = normalize_url(urljoin(url, target))
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                        raise AuditError("The URL does not return an HTML page.")
                    chunks, total = [], 0
                    for chunk in response.iter_content(chunk_size=16384):
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise AuditError("The page exceeds the 2 MB scan limit.")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    response.encoding = response.encoding or "utf-8"
                    html = raw.decode(response.encoding, errors="replace")
                    return url, html, {"status_code": response.status_code, "content_type": content_type, "bytes": total}
            except requests.RequestException as exc:
                raise AuditError(f"Could not retrieve the website: {exc.__class__.__name__}.") from exc
        raise AuditError("The website redirected too many times.")
    finally:
        session.close()


def analyze_html(url: str, html: str, fetch_info: dict | None = None) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    checks: list[Check] = []

    def add(category, name, good, warning, detail, recommendation):
        checks.append(Check(category, name, "pass" if good else "warning" if warning else "fail", detail, recommendation if not good else "No action needed.", 10 if good else 5 if warning else 0))

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    add("Metadata", "Page title", 30 <= len(title) <= 60, bool(title), f"{len(title)} characters · {title or 'Missing'}", "Write a unique, descriptive title of approximately 30–60 characters.")
    descriptions = soup.find_all("meta", attrs={"name": re.compile(r"^description$", re.I)})
    description = descriptions[0].get("content", "").strip() if descriptions else ""
    add("Metadata", "Meta description", 70 <= len(description) <= 160, bool(description), f"{len(description)} characters · {description or 'Missing'}", "Write a compelling, relevant meta description of approximately 70–160 characters.")
    h1 = soup.find_all("h1")
    add("Content", "Single H1 heading", len(h1) == 1, len(h1) > 1, f"Found {len(h1)} H1 headings", "Use one clear primary H1 heading on this page.")
    headings = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}
    add("Content", "Heading hierarchy", bool(h1) and not (headings["h3"] and not headings["h2"]), bool(h1), " · ".join(f"{key.upper()}: {count}" for key, count in headings.items()), "Use a logical heading structure without skipping major levels.")
    images = soup.find_all("img")
    missing_alt = [img for img in images if img.get("alt") is None]
    add("Images", "Image alt attributes", not missing_alt, bool(images) and len(missing_alt) < len(images), f"{len(images)} images · {len(missing_alt)} without alt attribute", "Add meaningful alt text to informative images; use empty alt for decorative images.")
    canonical = soup.find("link", rel=lambda v: bool(v) and "canonical" in (v if isinstance(v, list) else str(v).split()))
    canonical_url = canonical.get("href", "").strip() if canonical else ""
    add("Indexing", "Canonical URL", bool(canonical_url), False, canonical_url or "Missing", "Add a canonical link to indicate the preferred URL when appropriate.")
    viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    add("Mobile", "Viewport meta tag", bool(viewport and viewport.get("content")), False, viewport.get("content", "") if viewport else "Missing", "Include a responsive viewport meta tag.")
    lang = soup.html.get("lang", "").strip() if soup.html else ""
    add("Accessibility", "HTML language", bool(lang), False, lang or "Missing", "Declare the document language on the HTML element (for example, lang=\"en\").")
    robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots_content = robots.get("content", "") if robots else "Not specified (usually indexable)"
    noindex = bool(re.search(r"\bnoindex\b", robots_content, re.I))
    add("Indexing", "Indexing directive", not noindex, False, robots_content, "Remove noindex if the page should appear in search results.")
    add("Security", "HTTPS", urlsplit(url).scheme == "https", False, urlsplit(url).scheme.upper(), "Serve the website over HTTPS.")
    links = [a.get("href", "").strip() for a in soup.find_all("a", href=True)]
    empty_links = sum(1 for link in links if link in ("", "#") or link.lower().startswith("javascript:"))
    add("Links", "Link destinations", empty_links == 0, bool(links) and empty_links < len(links), f"{len(links)} links · {empty_links} empty or placeholder destinations", "Replace placeholder links with meaningful destinations or use buttons for actions.")
    score = round(100 * sum(c.points for c in checks) / sum(c.max_points for c in checks))
    return {
        "url": url, "audited_at": datetime.now(timezone.utc).isoformat(), "score": score,
        "grade": "Excellent" if score >= 90 else "Good" if score >= 75 else "Needs work" if score >= 50 else "Critical",
        "checks": [asdict(c) for c in checks],
        "summary": {status: sum(c.status == status for c in checks) for status in ("pass", "warning", "fail")},
        "page": {"title": title, "description": description, "headings": headings, "images": len(images), "links": len(links)},
        "fetch": fetch_info or {},
        "disclaimer": "Heuristic on-page HTML audit only. This is not a Google ranking score, Core Web Vitals test, full crawl, or guarantee of traffic/ROI.",
    }


def audit_website(url: str) -> dict:
    final_url, html, info = fetch_html(url)
    return analyze_html(final_url, html, info)


def export_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def export_html(report: dict) -> str:
    """Portable, printable report with all user-controlled strings escaped."""
    from html import escape
    rows = "".join(
        f"<tr><td>{escape(c['category'])}</td><td>{escape(c['name'])}</td><td>{escape(c['status'].upper())}</td><td>{escape(c['detail'])}</td><td>{escape(c['recommendation'])}</td></tr>"
        for c in report["checks"]
    )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SEO Audit Report</title><style>body{{font:15px system-ui,sans-serif;max-width:1100px;margin:48px auto;padding:0 22px;color:#1e293b}}h1{{color:#0f172a}}.score{{font-size:42px;font-weight:800;color:#4f46e5}}table{{border-collapse:collapse;width:100%}}th,td{{padding:12px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:top}}th{{background:#f1f5f9}}small{{color:#64748b}}@media print{{body{{margin:12px}}}}</style></head><body><h1>SEO Audit Lite</h1><p>{escape(report['url'])}</p><div class="score">{report['score']}/100</div><p>{escape(report['grade'])} · {escape(report['audited_at'])}</p><h2>Audit checks</h2><table><thead><tr><th>Category</th><th>Check</th><th>Status</th><th>Finding</th><th>Recommendation</th></tr></thead><tbody>{rows}</tbody></table><p><small>{escape(report['disclaimer'])}</small></p></body></html>'''
