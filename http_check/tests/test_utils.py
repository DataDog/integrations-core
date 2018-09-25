# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import tempfile
import shutil
import os
import sys

import pytest
import mock

from datadog_checks.http_check.utils import get_ca_certs_path, _get_ca_certs_paths


@pytest.mark.unit
def test_get_ca_certs_path():
    with pytest.raises(OSError):
        get_ca_certs_path()


@pytest.mark.unit
def test__get_ca_certs_paths():
    with mock.patch('datadog_checks.http_check.utils.os.path.dirname') as dirname:
        # create a tmp `embeddeded` folder
        tmp = tempfile.mkdtemp()
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
        print(paths)
        assert len(paths) == 3
        assert paths[1].endswith('ca-certificates.crt')
        assert paths[2] == '/etc/ssl/certs/ca-certificates.crt'

        shutil.rmtree(target)
