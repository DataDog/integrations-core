"""Render analysis/integrations/*.json into analysis/summary.md."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INT_DIR = ROOT / "analysis" / "integrations"
OUT = ROOT / "analysis" / "summary.md"


def load_all():
    out = []
    for p in sorted(INT_DIR.glob("*.json")):
        out.append(json.loads(p.read_text()))
    return out


def _refs(rec):
    parts = []
    for r in rec.get("references", []):
        kind = r["kind"]
        if "url" in r:
            parts.append(f"[{kind}]({r['url']})")
        elif "path" in r:
            parts.append(f"[{kind}](../{r['path']})")
    return ", ".join(parts) or "—"


def _row(rec):
    flag = " ⚠" if rec.get("needs_human_review") else ""
    expl = rec.get("explanation", "").replace("|", "\\|")
    fields = ", ".join(f"`{f}`" for f in rec.get("required_fields", [])) or "—"
    return (f"| {rec['display_name']}{flag} (`{rec['name']}`) "
            f"| {fields} "
            f"| {rec.get('auto_config_method', '')} — {expl} "
            f"| {_refs(rec)} |")


def _table(records, header):
    lines = [
        f"### {header}",
        "",
        "| Integration | Required fields | Method / detail | References |",
        "|---|---|---|---|",
    ]
    for rec in sorted(records, key=lambda r: r["name"]):
        lines.append(_row(rec))
    lines.append("")
    return "\n".join(lines)


def render(records, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counts = {"generic": 0, "custom": 0, "impossible": 0}
    review = 0
    for r in records:
        counts[r["classification"]] += 1
        if r.get("needs_human_review"):
            review += 1
    total = len(records)
    out = []
    out.append(
        f"_Generated {generated_at}. {total} total: "
        f"{counts['generic']} generic / {counts['custom']} custom / "
        f"{counts['impossible']} impossible / {review} need review (⚠)._\n"
    )
    by_cls = {"generic": [], "custom": [], "impossible": []}
    for r in records:
        by_cls[r["classification"]].append(r)
    out.append(_table(by_cls["generic"], "Generic auto-config possible"))
    out.append(_table(by_cls["custom"], "Custom auto-config possible"))
    out.append(_table(by_cls["impossible"], "Auto-config impossible"))
    return "\n".join(out)


def main():
    records = load_all()
    OUT.write_text(render(records))
    print(f"wrote {OUT} ({len(records)} integrations)")


if __name__ == "__main__":
    main()
