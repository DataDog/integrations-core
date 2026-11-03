# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from pathlib import Path

import pytest

from ddev.repo.config import RepositoryConfig, RepositoryConfigError
from ddev.utils.fs import Path as DdevPath
from ddev.utils.json import JSONPointerFile


def write_config(tmp_path: Path, main: str, imported: dict[str, str] | None = None) -> RepositoryConfig:
    config_dir = DdevPath(tmp_path, '.ddev')
    config_dir.mkdir()
    (config_dir / 'config.toml').write_text(main)
    for name, content in (imported or {}).items():
        (config_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (config_dir / name).write_text(content)
    return RepositoryConfig(config_dir / 'config.toml')


def test_core_functionality():
    assert issubclass(RepositoryConfig, JSONPointerFile)


def test_imports_are_merged(tmp_path: Path):
    config = write_config(
        tmp_path,
        'imports = ["dispatcher.toml"]\n\n[overrides.ci.disk]\nexclude = true\n',
        {'dispatcher.toml': '[dispatcher]\nworkflow_ref = "main"\n'},
    )

    assert config.get('/dispatcher/workflow_ref') == 'main'
    assert config.get('/overrides/ci/disk/exclude') is True
    assert 'imports' not in config.get('')


def test_imports_repeated_file_is_loaded_once(tmp_path: Path):
    config = write_config(
        tmp_path,
        'imports = ["dispatcher.toml", "./dispatcher.toml"]\n',
        {'dispatcher.toml': '[dispatcher]\nworkflow_ref = "main"\n'},
    )

    assert config.get('/dispatcher/workflow_ref') == 'main'


@pytest.mark.parametrize(
    ('main', 'imported', 'match'),
    [
        pytest.param(
            'imports = ["dispatcher.toml"]\n\n[dispatcher]\nworkflow_ref = "main"\n',
            {'dispatcher.toml': '[dispatcher.batching]\nmax_jobs_per_batch = 100\n'},
            r'`dispatcher`.*dispatcher\.toml',
            id='table split across the main and an imported file',
        ),
        pytest.param(
            'imports = ["first.toml", "second.toml"]\n',
            {
                'first.toml': '[dispatcher]\nworkflow_ref = "main"\n',
                'second.toml': '[dispatcher.batching]\nmax_jobs_per_batch = 100\n',
            },
            r'`dispatcher`.*first\.toml.*second\.toml',
            id='table split across imported files',
        ),
        pytest.param(
            'imports = ["dispatcher.toml"]\n',
            {'dispatcher.toml': 'imports = ["other.toml"]\n'},
            'nested imports',
            id='nested imports',
        ),
        pytest.param(
            'imports = ["config.toml"]\n',
            {},
            'imports the file itself',
            id='self import',
        ),
        pytest.param(
            'imports = ["nope.toml"]\n',
            {},
            'does not exist',
            id='missing file',
        ),
        pytest.param(
            'imports = ["subdir"]\n',
            {'subdir/dispatcher.toml': ''},
            'is not a file',
            id='directory',
        ),
        pytest.param(
            'imports = [\n',
            {},
            r'config\.toml is not valid TOML',
            id='invalid main file',
        ),
        pytest.param(
            'imports = ["dispatcher.toml"]\n',
            {'dispatcher.toml': '[dispatcher\n'},
            r'dispatcher\.toml is not valid TOML',
            id='invalid imported file',
        ),
        pytest.param(
            'imports = ["../outside.toml"]\n',
            {},
            'escapes',
            id='path escapes the config directory',
        ),
        pytest.param(
            'imports = "dispatcher.toml"\n',
            {'dispatcher.toml': ''},
            'must be a list',
            id='imports is not a list',
        ),
        pytest.param(
            'imports = ["dispatcher.toml", 1]\n',
            {'dispatcher.toml': ''},
            'must be a list',
            id='imports element is not a string',
        ),
    ],
)
def test_imports_invalid(tmp_path: Path, main: str, imported: dict[str, str], match: str):
    config = write_config(tmp_path, main, imported)

    with pytest.raises(RepositoryConfigError, match=match):
        config.get('')


def test_imports_absolute_path_rejected(tmp_path: Path):
    absolute = tmp_path / 'elsewhere.toml'
    # A TOML literal string, so Windows backslashes are not read as escapes.
    config = write_config(tmp_path, f"imports = ['{absolute}']\n")

    with pytest.raises(RepositoryConfigError, match='must be relative'):
        config.get('')


@pytest.mark.skipif(os.name == 'nt', reason='creating symlinks on Windows requires elevated privileges')
def test_imports_symlink_escape_rejected(tmp_path: Path):
    (tmp_path / 'outside.toml').write_text('[dispatcher]\nworkflow_ref = "main"\n')
    config = write_config(tmp_path, 'imports = ["linked.toml"]\n')
    (tmp_path / '.ddev' / 'linked.toml').symlink_to(tmp_path / 'outside.toml')

    with pytest.raises(RepositoryConfigError, match='escapes'):
        config.get('')


def test_save_refuses_when_imports_declared(tmp_path: Path):
    config = write_config(
        tmp_path,
        'imports = ["dispatcher.toml"]\n',
        {'dispatcher.toml': '[dispatcher]\nworkflow_ref = "main"\n'},
    )

    config.set('/dispatcher/workflow_ref', 'dev')

    with pytest.raises(RepositoryConfigError, match='Refusing to save'):
        config.save()
