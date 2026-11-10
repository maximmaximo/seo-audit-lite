# 🔎 SEO Audit Lite

**A free, open-source on-page SEO analyzer built with Python and Streamlit.**

SEO Audit Lite helps marketers, small business owners, and website consultants quickly review common HTML SEO signals and export actionable audit reports.

## Features

- 🌐 Analyze any publicly accessible HTML page by URL
- 📊 Transparent SEO score (0–100) across 11 weighted-equally checks
- 📝 Title and meta description length guidance
- 🧱 H1 presence/count and basic heading hierarchy review
- 🖼️ Missing image `alt` attribute detection
- 🔗 Canonical, robots noindex, HTTPS, and placeholder link checks
- 📱 Viewport and HTML language checks
- 🧭 Filter results by category and status
- 📥 Export printable HTML or machine-readable JSON reports
- 🔒 Blocks local/private network targets, caps downloads at 2 MB, limits redirects and timeouts

## Quick start

Requires **Python 3.10+**.

```bash
git clone https://github.com/YOUR_USERNAME/seo-audit-lite.git
cd seo-audit-lite
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and launch:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit (typically `http://localhost:8501`). Enter a public URL and click **Analyze website**.

## Deploy for free on Streamlit Community Cloud

1. Create a public GitHub repository named `seo-audit-lite` and push these files.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Select **Create app**, choose your repository and branch.
4. Set the entrypoint to `app.py` and deploy.
5. Add the resulting live demo URL to your GitHub repository description and README.

> Deployment requires a network environment that can fetch public websites. Some sites may block automated requests.

## Example output

```text
URL: https://example.com/
SEO Score: 75/100 (Good)
Checks: 7 passed · 3 warnings · 1 failed
Suggested action: Add a canonical link to indicate the preferred URL.
```

*Example is illustrative; actual results depend on the target page.*

## Project structure

```text
seo-audit-lite/
├── app.py                     # Streamlit UI
├── seo_audit/
│   ├── __init__.py
│   └── audit.py               # Fetching, SEO checks, and report exports
├── tests/test_audit.py        # Unit tests
├── .streamlit/config.toml     # Theme settings
├── .github/workflows/tests.yml# GitHub Actions test workflow
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
└── README.md
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Scope and limitations

This is a **single-page, HTML-based heuristic audit**. It does not crawl an entire domain, execute JavaScript, verify external links, measure page speed or Core Web Vitals, inspect robots.txt or XML sitemaps, or access Google Search Console. Its score is **not** a Google ranking score and does not predict traffic, revenue, or ROI. Suggested character lengths are editorial guidelines, not search-engine requirements.

For security, the application rejects private/reserved DNS results and IP addresses, disallows nonstandard ports, and revalidates each redirect. DNS rebinding remains possible between validation and connection: production multi-tenant deployments should also enforce outbound firewall / network egress restrictions. Only scan websites you have permission to assess. Do not expose this tool as an unrestricted high-volume crawler.

## License

MIT. See [LICENSE](LICENSE).
