"""Build the full Confluence body HTML: Introduction (verbatim) + Analysis.

The Introduction text mirrors the source ticket and is preserved word-for-word.
The Analysis section is rendered from analysis/summary.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "scripts"))
from render_html import to_html  # noqa: E402

SUMMARY = ROOT / "analysis" / "summary.md"

INTRODUCTION_HTML = """\
<h1>Introduction</h1>
<p>There is currently some support for auto configuration of agent integrations based on templated but this is only used by a small minority of available integrations since its capability is very limited (basically filling out the host and the highest-numbered port). This kind of logic is insufficient for many integrations since the port on which their metrics are known is freely configurable in the servers. So it requires some kind of probing to find out what is the correct config to use (what we refer to as &ldquo;advanced auto config&rdquo; in this document). There are various possible kinds of integrations:</p>
<ul>
<li>Integrations for which configuration requires credential not available from config files (eg postgres). Here advanced auto config may not be possible (to be double checked).</li>
<li>Integrations for which configuration requires only the port and the host (eg. krakend). These could be supported by a general &ldquo;scan ports till one looks like openmetrics&rdquo; advanced auto config method.</li>
<li>Integrations which which configuration requests the port and the URL path (eg. nginx which has a couple of alternatives which depend on the plugin used in the server). These need may need some integration-specific advanced auto config to find the correct endpoint automatically.</li>
<li>Other types not yet considered (there are 200+ integrations in integrations-core) so there could be many variations.</li>
</ul>
<p>So we need to analyze each integration one by one, look at the required fields of its configuration (they should be in <code>spec.yaml</code> for example), and analyze if that is something that could possibly be discovered automatically, and how. If generic port scanning is something that would be sufficient for the integration we should prefer that, since e.g. having code to find and parse each server&rsquo;s config files is much more work to implement and maintain.</p>
<p>The tables can be split based on the type of auto config possibility (possible generically, possible with custom logic or impossible). In the tables, we should list the integration, the required fields in the config, as well as a column with a detailed explanation (if necessary &ndash; if many integrations just use an OpenMetrics endpoint no need to be verbose about it) with links to sources (if any) justifying the auto config possibility.</p>
<h2>Analysis</h2>
"""


def build():
    summary_md = SUMMARY.read_text()
    return INTRODUCTION_HTML + to_html(summary_md)


def main():
    print(build())


if __name__ == "__main__":
    main()
