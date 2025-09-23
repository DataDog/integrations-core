# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.repo.core import Repository


@pytest.fixture
def fake_repo(tmp_path_factory, config_file, ddev):
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    config_file.model.repos['core'] = str(repo.path)
    config_file.save()

    for integration in ('dummy', 'no_metrics', 'no_metadata_file'):
        write_file(
            repo_path / integration,
            'pyproject.toml',
            f"""[project]
    name = "{integration}"
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.12",
    ]
    """,
        )

        write_file(repo_path / integration, 'manifest.json', "{}")

        write_file(
            repo_path / integration,
            'hatch.toml',
            """[env.collectors.datadog-checks]

        [[envs.default.matrix]]
        python = ["3.12"]

        """,
        )

    write_file(
        repo_path / 'dummy',
        'metadata.csv',
        """metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
dummy.metric,gauge,10,seconds,object,description,0,dummy,short,""",
    )

    write_file(
        repo_path / 'no_metrics',
        'metadata.csv',
        "metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric",
    )

    yield repo


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)
