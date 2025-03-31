# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test(ddev, config_file):
    result = ddev("config", "find")

    assert result.exit_code == 0, result.output
    assert result.output == f"{config_file.path}\n"


def test_with_overrides(ddev, config_file, tmp_path, monkeypatch):
    overrides_file = tmp_path / ".ddev.toml"
    overrides_file.write_text("")
    config_file.overrides_path = overrides_file

    with monkeypatch.context() as m:
        m.chdir(tmp_path)

        result = ddev("config", "find")

        assert result.exit_code == 0, result.output
        assert result.output == f"{config_file.path}\n----- Overrides applied from .ddev.toml\n"
