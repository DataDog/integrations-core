"""Build the full Confluence body markdown: Introduction + Analysis tables.

The Introduction text mirrors the source ticket and is preserved verbatim.
Local relative paths in summary.md are rewritten to absolute github.com URLs
so the links work when rendered on Confluence.

Usage:
    python3 build_confluence_body.py [verbose|brief]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY_VERBOSE = ROOT / "analysis" / "summary.md"
SUMMARY_BRIEF = ROOT / "analysis" / "summary_brief.md"
SUMMARY_COMPACT = ROOT / "analysis" / "summary_compact.md"

GITHUB_BASE = "https://github.com/DataDog/integrations-core/blob/master/"

INTRODUCTION_MD = """\
# Introduction

There is currently some support for auto configuration of agent integrations based on templated but this is only used by a small minority of available integrations since its capability is very limited (basically filling out the host and the highest-numbered port). This kind of logic is insufficient for many integrations since the port on which their metrics are known is freely configurable in the servers. So it requires some kind of probing to find out what is the correct config to use (what we refer to as "advanced auto config" in this document). There are various possible kinds of integrations:

* Integrations for which configuration requires credential not available from config files (eg postgres). Here advanced auto config may not be possible (to be double checked).
* Integrations for which configuration requires only the port and the host (eg. krakend). These could be supported by a general "scan ports till one looks like openmetrics" advanced auto config method.
* Integrations which which configuration requests the port and the URL path (eg. nginx which has a couple of alternatives which depend on the plugin used in the server). These need may need some integration-specific advanced auto config to find the correct endpoint automatically.
* Other types not yet considered (there are 200+ integrations in integrations-core) so there could be many variations.

So we need to analyze each integration one by one, look at the required fields of its configuration (they should be in `spec.yaml` for example), and analyze if that is something that could possibly be discovered automatically, and how. If generic port scanning is something that would be sufficient for the integration we should prefer that, since e.g. having code to find and parse each server's config files is much more work to implement and maintain.

The tables can be split based on the type of auto config possibility (possible generically, possible with custom logic or impossible). In the tables, we should list the integration, the required fields in the config, as well as a column with a detailed explanation (if necessary -- if many integrations just use an OpenMetrics endpoint no need to be verbose about it) with links to sources (if any) justifying the auto config possibility.

## Analysis

"""


def rewrite_links(md):
    return re.sub(r"\]\(\.\./([^)]+)\)", lambda m: f"]({GITHUB_BASE}{m.group(1)})", md)


def build(mode="verbose"):
    src = {
        "brief": SUMMARY_BRIEF,
        "compact": SUMMARY_COMPACT,
        "verbose": SUMMARY_VERBOSE,
    }.get(mode, SUMMARY_VERBOSE)
    return INTRODUCTION_MD + rewrite_links(src.read_text())


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verbose"
    sys.stdout.write(build(mode))


if __name__ == "__main__":
    main()
