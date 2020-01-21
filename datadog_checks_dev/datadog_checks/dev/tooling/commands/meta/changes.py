# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict, deque

import click

from ....subprocess import run_command
from ....utils import chdir, write_file
from ...constants import get_root
from ...utils import load_manifest
from ..console import CONTEXT_SETTINGS, echo_info


def validate_date(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return

    if not re.match(r'\d{4}-\d{2}-\d{2}', value):
        raise click.BadParameter('needs to be in YYYY-MM-DD format')

    return value


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Show changes since a specific date')
@click.argument('since', callback=validate_date)
@click.option('--out', '-o', 'out_file', is_flag=True, help='Output to file')
@click.option('--eager', is_flag=True, help='Skip validation of commit subjects')
def changes(since, out_file, eager):
    """Show changes since a specific date."""
    root = get_root()
    history_data = defaultdict(lambda: {'lines': deque(), 'releasers': set()})

    with chdir(root):
        result = run_command(
            (
                'git log "--pretty=format:%H %s" --date-order --date=iso8601 '
                '--since="{}T00:00:00" */CHANGELOG.md'.format(since)
            ),
            capture=True,
            check=True,
        )

        for result_line in result.stdout.splitlines():
            commit_hash, commit_subject = result_line.split(' ', 1)

            if not eager and 'release' not in commit_subject.lower():
                continue

            result = run_command(
                f'git show "--pretty=format:%an%n" -U0 {commit_hash} */CHANGELOG.md', capture=True, check=True
            )

            # Example:
            #
            # <AUTHOR NAME>
            # diff --git a/<INTEGRATION NAME 1>/CHANGELOG.md b/<INTEGRATION NAME 1>/CHANGELOG.md
            # index 89b5a3441..9534019a9 100644
            # --- a/<INTEGRATION NAME 1>/CHANGELOG.md
            # +++ b/<INTEGRATION NAME 1>/CHANGELOG.md
            # @@ -2,0 +3,5 @@
            # +## <RELEASE VERSION> / <RELEASE DATE>
            # +
            # +* <ENTRY>
            # +* <ENTRY>
            # +
            # diff --git a/<INTEGRATION NAME 2>/CHANGELOG.md b/<INTEGRATION NAME 2>/CHANGELOG.md
            # index 89b5a3441..9534019a9 100644
            # --- a/<INTEGRATION NAME 2>/CHANGELOG.md
            # +++ b/<INTEGRATION NAME 2>/CHANGELOG.md
            # @@ -2,0 +3,4 @@
            # +## <RELEASE VERSION> / <RELEASE DATE>
            # +
            # +* <ENTRY>
            # +
            lines = deque(result.stdout.splitlines())
            author_name = lines.popleft().strip()

            patches = []
            for line in lines:
                if line:
                    # New patch
                    if line.startswith('diff --git'):
                        patches.append([])
                    patches[-1].append(line)

            for patch in patches:
                integration = patch[0].split('/')[-2].strip()

                additions = deque()
                for line in reversed(patch):
                    if line.startswith('+'):
                        line = line[1:]
                        # Demote releases to h3
                        if line.startswith('##'):
                            line = f'#{line}'
                        additions.append(line)
                    elif line.startswith('@@'):
                        break

                # Get rid of the header for new integrations
                if additions[-1].startswith('# '):
                    additions.pop()

                # Get rid of blank lines to ensure consistency
                while additions and not additions[0].strip():
                    additions.popleft()
                while additions and not additions[-1].strip():
                    additions.pop()

                if additions:
                    history_data[integration]['releasers'].add(author_name)
                    history_data[integration]['lines'].appendleft('')
                    history_data[integration]['lines'].extendleft(additions)

    output_lines = [f'# Changes since {since}', '']

    for integration, history in sorted(history_data.items()):
        display_name = load_manifest(integration).get('display_name', integration)
        output_lines.append(f'## {display_name}')
        output_lines.append(f"released by: {', '.join(sorted(history['releasers']))}")

        output_lines.append('')
        output_lines.extend(history['lines'])

    output = '\n'.join(output_lines)

    if out_file:
        write_file(out_file, output)
    else:
        echo_info(output)
