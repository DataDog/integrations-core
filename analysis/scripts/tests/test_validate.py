import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATE = ROOT / "scripts" / "validate.py"

VALID = {
    "name": "redisdb",
    "display_name": "Redis",
    "spec_path": "redisdb/assets/configuration/spec.yaml",
    "required_fields": ["host", "port"],
    "all_relevant_fields": [
        {"name": "host", "required": True, "default": "localhost"}
    ],
    "classification": "generic",
    "auto_config_method": "tcp-banner-probe",
    "has_existing_auto_conf": True,
    "auto_conf_path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml",
    "explanation": "Redis answers a banner; default port 6379.",
    "references": [{"kind": "spec", "path": "redisdb/assets/configuration/spec.yaml"}],
    "confidence": "high",
    "needs_human_review": False,
}


def _run(payload, tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps(payload))
    return subprocess.run(
        [sys.executable, str(VALIDATE), str(f)],
        capture_output=True, text=True
    )


def test_valid_passes(tmp_path):
    r = _run(VALID, tmp_path)
    assert r.returncode == 0, r.stderr


def test_missing_required_field_fails(tmp_path):
    bad = dict(VALID)
    del bad["classification"]
    r = _run(bad, tmp_path)
    assert r.returncode != 0
    assert "classification" in r.stderr


def test_bad_enum_fails(tmp_path):
    bad = dict(VALID)
    bad["classification"] = "maybe"
    r = _run(bad, tmp_path)
    assert r.returncode != 0


def test_unknown_field_fails(tmp_path):
    bad = dict(VALID)
    bad["typo_field"] = "oops"
    r = _run(bad, tmp_path)
    assert r.returncode != 0
    assert "typo_field" in r.stderr


def test_bad_pattern_fails(tmp_path):
    bad = dict(VALID)
    bad["name"] = "Has-Caps-And-Dashes"
    r = _run(bad, tmp_path)
    assert r.returncode != 0
