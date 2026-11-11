"""SEO Audit Lite — Streamlit application."""
import pandas as pd
import streamlit as st
from seo_audit.audit import AuditError, audit_website, export_html, export_json

st.set_page_config(page_title="SEO Audit Lite | Website SEO Analyzer", page_icon="🔎", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp {background: #f7f9fd; color: #14233d;}
.block-container {max-width: 1150px; padding-top: 2.5rem;}
.hero {background: linear-gradient(125deg,#111d45,#3730a3 70%,#5b5fe7);border-radius:22px;padding:40px;color:white;margin-bottom:26px;box-shadow:0 14px 35px #202d6620}
.hero h1 {font-size:2.6rem;letter-spacing:-.05em;margin:0 0 10px;color:white}
.hero p {font-size:1.08rem;color:#dce2ff;margin:0;max-width:700px}
.eyebrow {text-transform:uppercase;letter-spacing:.16em;font-size:.72rem;font-weight:700;color:#a5b4fc;margin-bottom:12px}
div[data-testid="stMetric"] {background:white;border:1px solid #e4eaf3;border-radius:16px;padding:16px 20px;box-shadow:0 3px 15px #152c4b08}
div[data-testid="stMetricLabel"] {color:#5b6780}
div[data-testid="stMetricValue"] {font-size:clamp(1.25rem, 2.1vw, 2rem);overflow-wrap:anywhere;line-height:1.3}
.audit-rating {background:#fff;border:1px solid #e4eaf3;border-radius:16px;padding:15px 20px;box-shadow:0 3px 15px #152c4b08;min-height:112px}
.audit-rating-label {font-size:.88rem;color:#5b6780;margin-bottom:9px}
.audit-rating-value {font-size:1.35rem;font-weight:700;color:#14233d;line-height:1.25;overflow-wrap:anywhere}
.audit-note {color:#64748b;font-size:.88rem}
.stButton>button[kind="primary"] {background:#4f46e5;border-radius:10px;border:0;font-weight:700}
section[data-testid="stSidebar"] {background:#fff}
</style>""", unsafe_allow_html=True)

st.markdown('<div class="hero"><div class="eyebrow">Free on-page SEO toolkit</div><h1>SEO Audit Lite 🔎</h1><p>Find on-page SEO issues in seconds. Review metadata, headings, images, indexing signals, and practical optimization recommendations.</p></div>', unsafe_allow_html=True)

with st.form("scan_form"):
    left, right = st.columns([4, 1], vertical_alignment="bottom")
    with left:
        website = st.text_input("Website URL", placeholder="https://example.com", help="Only publicly reachable HTML websites are supported.")
    with right:
        submit = st.form_submit_button("Analyze website →", type="primary", width="stretch")

if submit:
    with st.spinner("Fetching and analyzing the page..."):
        try:
            st.session_state["report"] = audit_website(website)
            st.session_state.pop("error", None)
        except AuditError as exc:
            st.session_state["error"] = str(exc)
            st.session_state.pop("report", None)
        except Exception:
            import logging
            logging.exception("Unexpected SEO audit failure")
            st.session_state["error"] = "The audit could not be completed. Please try another public website."
            st.session_state.pop("report", None)

if st.session_state.get("error"):
    st.error(st.session_state["error"])

report = st.session_state.get("report")
if report:
    st.markdown("### Your audit results")
    st.caption(f"Analyzed URL: {report['url']} · {report['audited_at'][:19].replace('T', ' ')} UTC")
    cols = st.columns([1.1, 1.55, 1, 1, 1], gap="small")
    cols[0].metric("SEO score", f"{report['score']}/100")
    # The rating is rendered in a flexible card so longer labels never get truncated.
    with cols[1]:
        st.markdown(
            '<div class="audit-rating"><div class="audit-rating-label">Rating</div>'
            f'<div class="audit-rating-value">{report["grade"]}</div></div>',
            unsafe_allow_html=True,
        )
    for col, label, status in zip(cols[2:], ("Passed", "Warnings", "Failed"), ("pass", "warning", "fail")):
        col.metric(label, report["summary"][status])
    st.progress(report["score"] / 100)
    st.caption("The score is a transparent heuristic based on 11 on-page checks, not a Google metric.")
    st.markdown("#### Detailed checks")
    categories = ["All categories"] + sorted({c["category"] for c in report["checks"]})
    cat = st.selectbox("Filter by category", categories)
    statuses = st.multiselect("Show statuses", ["pass", "warning", "fail"], default=["pass", "warning", "fail"])
    checks = [c for c in report["checks"] if (cat == "All categories" or c["category"] == cat) and c["status"] in statuses]
    if checks:
        frame = pd.DataFrame(checks)[["category", "name", "status", "detail", "recommendation"]]
        frame.columns = ["Category", "Check", "Status", "Finding", "Recommendation"]
        st.dataframe(
            frame,
            width="stretch",
            hide_index=True,
            row_height=54,
            height=min(680, 54 * (len(frame) + 1) + 8),
            column_config={
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Check": st.column_config.TextColumn("Check", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Finding": st.column_config.TextColumn("Finding", width="large"),
                "Recommendation": st.column_config.TextColumn("Recommendation", width="large"),
            },
        )
        st.caption("Tip: hover over a cell to read long text, or expand a priority recommendation below.")
    else:
        st.info("No checks match the selected filters.")
    issues = [c for c in report["checks"] if c["status"] != "pass"]
    if issues:
        st.markdown("#### Priority recommendations")
        for c in sorted(issues, key=lambda x: x["points"]):
            with st.expander(f"{'🔴' if c['status'] == 'fail' else '🟠'} {c['name']} · {c['category']}"):
                st.write(f"**Finding:** {c['detail']}")
                st.write(f"**Suggested action:** {c['recommendation']}")
    else:
        st.success("All available on-page checks passed. Keep monitoring your content and technical SEO.")
    st.markdown("#### Export your report")
    c1, c2 = st.columns(2)
    c1.download_button("⬇ Download HTML report", export_html(report), file_name="seo-audit-report.html", mime="text/html", width="stretch")
    c2.download_button("⬇ Download JSON data", export_json(report), file_name="seo-audit-report.json", mime="application/json", width="stretch")
else:
    st.markdown("### What we check")
    a, b, c = st.columns(3)
    with a:
        st.markdown("**📝 Metadata & content**")
        st.write("Page title, meta description, H1 count, and heading hierarchy.")
    with b:
        st.markdown("**🖼️ Images & usability**")
        st.write("Image alt attributes, viewport settings, and document language.")
    with c:
        st.markdown("**🔗 Indexing & links**")
        st.write("Canonical URL, robots meta directive, HTTPS, and link destinations.")

st.divider()
st.caption("SEO Audit Lite v1.1 · Free, open-source, single-page HTML analyzer. It does not measure Core Web Vitals, crawl an entire site, or predict Google rankings. Scan only sites you are authorized to assess.")
