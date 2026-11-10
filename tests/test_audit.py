import pytest
from seo_audit.audit import AuditError, analyze_html, export_html, normalize_url, validate_public_url

HTML = '''<!doctype html><html lang="en"><head><title>Example Business Offers Excellent Services in Your City</title><meta name="description" content="Explore our reliable business services, discover practical solutions, and contact our friendly team for expert support and guidance today."><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="canonical" href="https://example.com/"></head><body><h1>Business services</h1><h2>Our work</h2><img src="a.jpg" alt="Team at work"><a href="/about">About</a></body></html>'''

def test_normalization():
    assert normalize_url("example.com") == "https://example.com/"
    assert normalize_url("https://example.com/a#fragment") == "https://example.com/a"

@pytest.mark.parametrize("value", ["ftp://example.com", "https://user:pass@example.com", "https://example.com:8080"])
def test_reject_unsupported(value):
    with pytest.raises(AuditError):
        normalize_url(value)

@pytest.mark.parametrize("value", ["http://127.0.0.1/", "http://169.254.169.254/", "http://localhost/", "http://[::1]/"])
def test_block_private(value):
    with pytest.raises(AuditError):
        validate_public_url(normalize_url(value))

def test_good_page():
    result = analyze_html("https://example.com/", HTML)
    assert result["score"] >= 90
    assert len(result["checks"]) == 11
    assert result["summary"]["fail"] == 0

def test_missing_metadata():
    result = analyze_html("http://example.com/", "<html><body><img src='a'><h2>Hi</h2></body></html>")
    assert result["score"] < 50
    assert result["summary"]["fail"] >= 5

def test_noindex():
    result = analyze_html("https://example.com/", HTML.replace("</head>", '<meta name="robots" content="noindex,follow"></head>'))
    assert next(c for c in result["checks"] if c["name"] == "Indexing directive")["status"] == "fail"

def test_export_escapes_html():
    result = analyze_html("https://example.com/", '<html><head><title><script>alert(1)</script></title></head></html>')
    html = export_html(result)
    assert "&lt;" not in result["page"]["title"]
    assert "<script>" not in html
