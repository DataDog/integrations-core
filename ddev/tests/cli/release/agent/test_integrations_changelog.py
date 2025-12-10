# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest


def test_integrations_changelog_without_arguments(fake_changelogs, ddev):
    result = ddev('release', 'agent', 'integrations-changelog')

    assert result.exit_code == 0
    expected_output = '\n'.join(
        [
            fake_changelogs['datadog_checks_downloader'],
            fake_changelogs['bar'],
            fake_changelogs['datadog_checks_base'],
            fake_changelogs['foo'],
        ]
    )
    assert result.output.rstrip('\n') == expected_output.rstrip('\n')


def test_integrations_changelog_specific_check(fake_changelogs, ddev):
    result = ddev('release', 'agent', 'integrations-changelog', 'foo')
    assert result.exit_code == 0
    assert result.output.rstrip('\n') == fake_changelogs['foo'].rstrip('\n')


def test_integrations_changelog_write(repo_with_fake_changelogs, ddev):
    repo, fake_changelogs = repo_with_fake_changelogs

    result = ddev('release', 'agent', 'integrations-changelog', '--write')
    assert result.exit_code == 0
    with open(repo.path / 'foo' / 'CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelogs['foo'].rstrip('\n')

    with open(repo.path / 'bar' / 'CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelogs['bar'].rstrip('\n')

    with open(repo.path / 'datadog_checks_base' / 'CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelogs['datadog_checks_base'].rstrip('\n')

    with open(repo.path / 'datadog_checks_downloader' / 'CHANGELOG.md') as f:
        assert f.read().rstrip('\n') == fake_changelogs['datadog_checks_downloader'].rstrip('\n')


@pytest.fixture
def repo_with_fake_changelogs(repo_with_history, config_file):
    repo_root = repo_with_history.path

    config_file.model.repos['core'] = str(repo_with_history.path)
    config_file.save()

    # Write a changelog for a couple of integrations
    (repo_root / 'foo' / 'CHANGELOG.md').write_text(
        """# CHANGELOG - foo
## 1.5.0 / 2022-09-16

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 1.0.0 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))
"""
    )
    (repo_root / 'bar' / 'CHANGELOG.md').write_text(
        """# CHANGELOG - bar
## 2.0.0 / 2022-11-16

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))

## 1.0.0 / 2022-05-18

***Fixed***:

* Remove unused `metric_prefix` in init_config ([#11464](https://github.com/DataDog/integrations-core/pull/11464))
"""
    )
    (repo_root / 'datadog_checks_downloader' / 'CHANGELOG.md').write_text(
        """# CHANGELOG - datadog_checks_downloader
## 4.0.0 / 2022-11-16

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
"""
    )
    (repo_root / 'datadog_checks_base' / 'CHANGELOG.md').write_text(
        """# CHANGELOG - datadog_checks_base
## 3.0.0 / 2022-11-16

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
"""
    )
    # Turn 'foo' and 'bar' into *valid checks* by giving them an __about__.py file in the right location
    (repo_root / 'foo' / 'datadog_checks' / 'foo').mkdir(parents=True)
    (repo_root / 'foo' / 'datadog_checks' / 'foo' / '__about__.py').touch()
    (repo_root / 'bar' / 'datadog_checks' / 'bar').mkdir(parents=True)
    (repo_root / 'bar' / 'datadog_checks' / 'bar' / '__about__.py').touch()
    (repo_root / 'datadog_checks_downloader' / 'datadog_checks' / 'downloader').mkdir(parents=True)
    (repo_root / 'datadog_checks_downloader' / 'datadog_checks' / 'downloader' / '__about__.py').touch()
    (repo_root / 'datadog_checks_base' / 'datadog_checks' / 'base').mkdir(parents=True)
    (repo_root / 'datadog_checks_base' / 'datadog_checks' / 'base' / '__about__.py').touch()

    # The fixture's value is a dictionary with the expected values for each integration
    expected_changelogs = {
        'foo': """# CHANGELOG - foo
## 1.5.0 / 2022-09-16 / Agent 7.38.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 1.0.0 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))
""",
        'bar': """# CHANGELOG - bar
## 2.0.0 / 2022-11-16 / Agent 7.39.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))

## 1.0.0 / 2022-05-18 / Agent 7.38.0

***Fixed***:

* Remove unused `metric_prefix` in init_config ([#11464](https://github.com/DataDog/integrations-core/pull/11464))
""",
        'datadog_checks_downloader': """# CHANGELOG - datadog_checks_downloader
## 4.0.0 / 2022-11-16 / Agent 7.41.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
""",
        'datadog_checks_base': """# CHANGELOG - datadog_checks_base
## 3.0.0 / 2022-11-16 / Agent 7.39.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
""",
    }
    return repo_with_history, expected_changelogs


@pytest.fixture
def fake_changelogs(repo_with_fake_changelogs):
    _, fake_changelogs = repo_with_fake_changelogs
    return fake_changelogs
