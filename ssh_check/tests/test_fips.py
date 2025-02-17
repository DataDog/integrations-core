# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import paramiko
from mock import patch

from datadog_checks.ssh_check.ssh_check import patch_paramiko


def test_paramiko_uses_md5():
    '''
    By default, paramiko uses MD5 for the PKey.get_fingerprint function.
    If this is no longer the case, the patch can be removed.
    '''
    with patch("paramiko.pkey.md5") as mock_md5:
        paramiko.PKey().get_fingerprint()
        mock_md5.assert_called_once()


def test_patch():
    '''
    This test checks that the patch function works by verifying that hashlib.md5 is replaced by
    hashlib.sha256 in the get_fingerprint function.
    '''
    with patch("paramiko.pkey.md5") as mock_md5, patch("datadog_checks.ssh_check.ssh_check.sha256") as mock_sha256:
        patch_paramiko()
        mock_sha256.assert_not_called()  # Checking that the patch definition does not count as a function call
        paramiko.PKey().get_fingerprint()
        mock_md5.assert_not_called()
        mock_sha256.assert_called_once()
