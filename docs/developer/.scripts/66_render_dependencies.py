from base64 import urlsafe_b64decode

from datadog_checks.dev.tooling.constants import get_agent_requirements

MARKER = '<docs-insert-dependencies>'
OTHER_DEPENDENCY = urlsafe_b64decode('aHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g_dj1kUXc0dzlXZ1hjUQ==').decode('utf-8')


def patch(lines):
    """This renders the list of shipped dependencies."""
    if not lines or not (lines[0] == '# Acknowledgements' and MARKER in lines):
        return

    marker_index = lines.index(MARKER)
    new_lines = lines[:marker_index]

    agent_requirements = get_agent_requirements()

    dependencies = set()
    with open(agent_requirements, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                dependencies.add(line.split('==')[0].split('[')[0].strip().lower())

    new_lines.append('??? example "Dependencies"')
    new_lines.append('    === "Core"')
    for dep in sorted(dependencies):
        new_lines.append(f'        - [{dep}](https://pypi.org/project/{dep}/)')

    new_lines.append('')
    new_lines.append('    === "Other"')
    new_lines.append(f'        - [Rick]({OTHER_DEPENDENCY})')

    new_lines.extend(lines[marker_index + 1:])
    return new_lines
