# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def test(ddev, config_file):
    result = ddev('config', 'find')

    assert result.exit_code == 0, result.output
    assert result.output == f'{config_file.path}\n'
