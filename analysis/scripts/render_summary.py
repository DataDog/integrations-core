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


def render_brief(records, generated_at=None, header_note=""):
    """Compact rendering: integration | required fields | method | confidence."""
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
        f"{counts['impossible']} impossible / {review} need review (⚠).{header_note}_\n"
    )
    by_cls = {"generic": [], "custom": [], "impossible": []}
    for r in records:
        by_cls[r["classification"]].append(r)
    for header, key in [
        ("Generic auto-config possible", "generic"),
        ("Custom auto-config possible", "custom"),
        ("Auto-config impossible", "impossible"),
    ]:
        out.append(f"### {header}\n")
        out.append("| Integration | Required fields | Method | Conf. |")
        out.append("|---|---|---|---|")
        for rec in sorted(by_cls[key], key=lambda r: r["name"]):
            flag = " ⚠" if rec.get("needs_human_review") else ""
            fields = ", ".join(f"`{f}`" for f in rec.get("required_fields", [])) or "—"
            out.append(
                f"| {rec['display_name']}{flag} (`{rec['name']}`) | "
                f"{fields} | {rec.get('auto_config_method', '')} | "
                f"{rec.get('confidence', '')} |"
            )
        out.append("")
    return "\n".join(out)


def _trim_explanation(text, limit=240):
    """Cap an explanation at the nearest sentence boundary <= limit chars."""
    import re
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sentences:
        if len(out) + len(s) + 1 > limit and out:
            break
        out = (out + " " + s).strip() if out else s
    return out


def render_compact(records, generated_at=None):
    """Same shape as render() but with explanations trimmed to ~240 chars."""
    trimmed = [dict(r, explanation=_trim_explanation(r.get("explanation", ""))) for r in records]
    return render(trimmed, generated_at=generated_at)


def main():
    records = load_all()
    OUT.write_text(render(records))
    print(f"wrote {OUT} ({len(records)} integrations)")
    brief_path = OUT.with_name("summary_brief.md")
    brief_path.write_text(render_brief(records))
    print(f"wrote {brief_path}")
    compact_path = OUT.with_name("summary_compact.md")
    compact_path.write_text(render_compact(records))
    print(f"wrote {compact_path}")


if __name__ == "__main__":
    main()
