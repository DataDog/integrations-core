import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "render_summary", ROOT / "scripts" / "render_summary.py"
)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


DATA = [
    {
        "name": "redisdb", "display_name": "Redis",
        "classification": "generic",
        "discovery_bucket": "tcp-protocol-handshake",
        "required_fields": ["host", "port"],
        "auto_config_method": "tcp-banner-probe",
        "explanation": "PING banner.",
        "references": [{"kind": "spec", "path": "redisdb/assets/configuration/spec.yaml"}],
        "confidence": "high", "needs_human_review": False,
    },
    {
        "name": "nginx", "display_name": "NGINX",
        "classification": "custom",
        "discovery_bucket": "http-multi-path",
        "required_fields": ["nginx_status_url"],
        "auto_config_method": "http-path-probe",
        "explanation": "Multiple stub_status path conventions.",
        "references": [],
        "confidence": "medium", "needs_human_review": False,
    },
    {
        "name": "github", "display_name": "GitHub",
        "classification": "impossible",
        "discovery_bucket": "creds-api-token",
        "required_fields": ["github_app_id", "private_key"],
        "auto_config_method": "credentials-required",
        "explanation": "Needs app id + private key.",
        "references": [],
        "confidence": "high", "needs_human_review": False,
    },
]


def test_section_and_bucket_headers():
    out = render.render(DATA, generated_at="2026-04-30")
    assert "## Fully generic" in out
    assert "## TCP probe with integration-specific protocol" in out
    assert "## HTTP probe with integration-specific verification" in out
    assert "## Credentials required" in out
    assert "### `tcp-protocol-handshake`" in out
    assert "### `http-multi-path`" in out
    assert "### `creds-api-token`" in out
    assert "redisdb" in out
    assert "nginx" in out
    assert "github" in out


def test_counts_in_header():
    out = render.render(DATA, generated_at="2026-04-30")
    assert "1 generic" in out
    assert "1 custom" in out
    assert "1 impossible" in out


def test_needs_review_marker():
    data = [dict(DATA[0], needs_human_review=True)]
    out = render.render(data, generated_at="2026-04-30")
    assert "⚠" in out


def test_pipe_in_explanation_is_escaped():
    data = [dict(DATA[0], explanation="contains | pipe character")]
    out = render.render(data, generated_at="2026-04-30")
    table_line = next(l for l in out.splitlines() if l.startswith("|") and "redisdb" in l)
    assert "\\|" in table_line
