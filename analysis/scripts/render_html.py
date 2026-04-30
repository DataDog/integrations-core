"""Convert analysis/summary.md into Confluence-compatible HTML.

Handles only the markdown subset emitted by render_summary.py:
- '### heading'
- '_italic paragraph_'
- '| pipe | tables |'
- inline `code` and [link](href)
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "analysis" / "summary.md"

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE = re.compile(r"`([^`]+)`")


def inline(text):
    text = html.escape(text, quote=False)
    text = LINK.sub(r'<a href="\2">\1</a>', text)
    text = CODE.sub(r"<code>\1</code>", text)
    return text


def to_html(md):
    out = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:].strip())}</h3>")
            i += 1
            continue
        if line.startswith("|"):
            header = [c.strip() for c in line.strip("|").split("|")]
            i += 1  # skip separator row
            i += 1
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            thead = "<thead><tr>" + "".join(f"<th>{inline(h)}</th>" for h in header) + "</tr></thead>"
            tbody = "<tbody>" + "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                for row in rows
            ) + "</tbody>"
            out.append(f"<table>{thead}{tbody}</table>")
            continue
        if line.startswith("_") and line.endswith("_") and len(line) > 1:
            out.append(f"<p><em>{inline(line[1:-1])}</em></p>")
            i += 1
            continue
        if line.strip() == "":
            i += 1
            continue
        out.append(f"<p>{inline(line)}</p>")
        i += 1
    return "\n".join(out)


def main():
    md = SRC.read_text()
    print(to_html(md))


if __name__ == "__main__":
    main()
