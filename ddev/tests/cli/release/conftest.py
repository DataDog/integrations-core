# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shutil

import pytest

from ddev.utils.fs import Path
from tests.helpers.git import ClonedRepo


def reset_fragments_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


@pytest.fixture
def repo_with_towncrier(repository: ClonedRepo, helpers) -> ClonedRepo:
    (repository.path / 'towncrier.toml').write_text(
        helpers.dedent(
            r'''
            [tool.towncrier]
            # If you change the values for directory or filename, make sure to look for them in the code as well.
            directory = "changelog.d"
            filename = "CHANGELOG.md"
            start_string = "<!-- towncrier release notes start -->\n"
            underlines = ["", "", ""]
            template = "changelog_template.jinja"
            title_format = "## {version} / {project_date}"
            # We automatically link to PRs, but towncrier only has an issue template so we abuse that.
            issue_format = "([#{issue}](https://github.com/DataDog/integrations-core/pull/{issue}))"

            # The order of entries matters! It controls the order in which changelog sections are displayed.
            # https://towncrier.readthedocs.io/en/stable/configuration.html#use-a-toml-array-defined-order
            [[tool.towncrier.type]]
            directory="removed"
            name = "Removed"
            showcontent = true

            [[tool.towncrier.type]]
            directory="changed"
            name = "Changed"
            showcontent = true

            [[tool.towncrier.type]]
            directory="security"
            name = "Security"
            showcontent = true

            [[tool.towncrier.type]]
            directory="deprecated"
            name = "Deprecated"
            showcontent = true

            [[tool.towncrier.type]]
            directory="added"
            name = "Added"
            showcontent = true

            [[tool.towncrier.type]]
            directory="fixed"
            name = "Fixed"
            showcontent = true
            '''
        )
    )
    (repository.path / 'changelog_template.jinja').write_text(
        helpers.dedent(
            '''
            {% if sections[""] %}
            {% for category, val in definitions.items() if category in sections[""] %}
            ***{{ definitions[category]['name'] }}***:

            {% for text, values in sections[""][category].items() %}
            * {{ text }} {{ values|join(', ') }}
            {% endfor %}

            {% endfor %}
            {% else %}
            No significant changes.


            {% endif %}
            '''
        )
    )
    return repository
