# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest
import mock

from datadog_checks.dev import temp_dir
from datadog_checks.http_check.utils import get_ca_certs_path, _get_ca_certs_paths


@pytest.mark.unit
def test_get_ca_certs_path():
    with mock.patch('datadog_checks.http_check.utils._get_ca_certs_paths') as gp:
        # no certs found
        gp.return_value = []
        assert get_ca_certs_path() is None
        # one cert file was found
        # let's avoid creating a real file just for the sake of mocking a cert
        # and use __file__ instead
        gp.return_value = [__file__]
        assert get_ca_certs_path() == __file__


@pytest.mark.unit
def test__get_ca_certs_paths_ko():
    """
    When `embedded` folder is not found, it should raise OSError
    """
    with pytest.raises(OSError):
        _get_ca_certs_paths()


@pytest.mark.unit
def test__get_ca_certs_paths():
    with mock.patch('datadog_checks.http_check.utils.os.path.dirname') as dirname:
        # create a tmp `embeddeded` folder
        with temp_dir() as tmp:
            target = os.path.join(tmp, 'embedded')
            os.mkdir(target)
            # point `dirname()` there
            dirname.return_value = target

            # tornado not found
            paths = _get_ca_certs_paths()
            assert len(paths) == 2
            assert paths[0].startswith(target)
            assert paths[1] == '/etc/ssl/certs/ca-certificates.crt'

            # mock tornado's presence
            sys.modules['tornado'] = mock.MagicMock(__file__='.')
            paths = _get_ca_certs_paths()
            assert len(paths) == 3
            assert paths[1].endswith('ca-certificates.crt')
            assert paths[2] == '/etc/ssl/certs/ca-certificates.crt'
