# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl
from ssl import SSLContext

import pytest
from mock import MagicMock, patch

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tls import TlsContextWrapper
from datadog_checks.dev import TempDir


class TestCheckAttribute:
    def test_default(self):
        check = AgentCheck('test', {}, [{}])

        assert not hasattr(check, '_tls_context_wrapper')

    def test_activate(self):
        check = AgentCheck('test', {}, [{}])

        context = check.get_tls_context()
        assert context == check._tls_context_wrapper.tls_context
        assert isinstance(context, SSLContext)

    def test_refresh(self):
        check = AgentCheck('test', {}, [{}])

        context = check.get_tls_context()
        assert context == check.get_tls_context()
        assert context != check.get_tls_context(refresh=True)


class TestVerify:
    def test_default(self):
        tls = TlsContextWrapper({})
        assert tls.config['tls_verify'] is True

    def test_config(self):
        tls = TlsContextWrapper({'tls_verify': False})
        assert tls.config['tls_verify'] is False

    @pytest.mark.parametrize('param', ('tls_ca_cert', 'tls_cert', 'tls_private_key', 'tls_private_key_password'))
    def test_config_overwrite(self, param):
        config = {'tls_verify': False, param: 'foo'}
        with patch('ssl.SSLContext'):
            tls = TlsContextWrapper(config)
        assert tls.config['tls_verify'] is True


@pytest.mark.parametrize(
    'param', ('tls_ca_cert', 'tls_cert', 'tls_private_key', 'tls_private_key_password', 'tls_validate_hostname')
)
def test_attributes(param):
    config = {param: 'foo'}
    with patch('ssl.SSLContext'):
        tls = TlsContextWrapper(config)
    assert tls.config[param] == 'foo'


class TestRemapper:
    def test_no_default(self):
        remapper = {'verify': {'name': 'tls_verify'}}
        tls = TlsContextWrapper({}, remapper)
        assert tls.config['tls_verify'] is True

    def test_default(self):
        remapper = {'verify': {'name': 'tls_verify', 'default': False}}
        tls = TlsContextWrapper({}, remapper)
        assert tls.config['tls_verify'] is False

    def test_invert(self):
        instance = {'disable_tls_validation': True}
        remapper = {'disable_tls_validation': {'name': 'tls_verify', 'default': True, 'invert': True}}
        tls = TlsContextWrapper(instance, remapper)

        assert tls.config['tls_verify'] is False

    def test_invert_with_explicit_default(self):
        instance = {}
        remapper = {'disable_tls_validation': {'name': 'tls_verify', 'invert': True, 'default': True}}
        tls = TlsContextWrapper(instance, remapper)
        assert tls.config['tls_verify'] is False

    def test_invert_without_explicit_default(self):
        instance = {}
        remapper = {'disable_tls_validation': {'name': 'tls_verify', 'invert': True}}
        tls = TlsContextWrapper(instance, remapper)
        assert tls.config['tls_verify'] is True


class TestHigherPriorityRemapper:
    def test_verify_no_remapper(self):
        instance = {'tls_verify': False, '_tls_context_tls_verify': True}
        tls = TlsContextWrapper(instance)
        assert tls.config['tls_verify'] is True

    def test_verify_remapper(self):
        instance = {'disable_tls_validation': True, '_tls_context_tls_verify': True}
        remapper = {'disable_tls_validation': {'name': 'tls_verify', 'invert': True}}
        tls = TlsContextWrapper(instance, remapper)
        assert tls.config['tls_verify'] is True

    def test_verify_remapper_to_higher_priority(self):
        instance = {'disable_tls_validation': True, 'tls_verify': True}
        remapper = {'disable_tls_validation': {'name': '_tls_context_tls_verify', 'invert': True}}
        tls = TlsContextWrapper(instance, remapper)
        assert tls.config['tls_verify'] is False


class TestTLSContext:
    def test_unverified_tls(self):
        instance = {'tls_verify': False}
        check = AgentCheck('test', {}, [instance])
        assert check.get_tls_context().verify_mode == ssl.CERT_NONE

    def test_verify_ssl(self):
        instance = {'tls_verify': True, 'tls_validate_hostname': False}
        check = AgentCheck('test', {}, [instance])
        context = check.get_tls_context()
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is False

    def test_verify_ssl_with_hostname_by_default(self):
        instance = {'tls_verify': True}
        check = AgentCheck('test', {}, [instance])
        context = check.get_tls_context()
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True

    def test_verify_ssl_with_hostname(self):
        instance = {'tls_verify': True, 'tls_validate_hostname': True}
        check = AgentCheck('test', {}, [instance])
        context = check.get_tls_context()
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True

    def test_no_ca_certs_default(self):
        check = AgentCheck('test', {}, [{}])
        with patch('ssl.SSLContext'):
            context = check.get_tls_context()  # type: MagicMock
            context.load_default_certs.assert_called_with(ssl.Purpose.SERVER_AUTH)

    def test_ca_cert_file(self):
        with patch('ssl.SSLContext'), TempDir("test_ca_cert_file") as tmp_dir:
            filename = os.path.join(tmp_dir, 'foo')
            open(filename, 'w').close()
            instance = {'tls_ca_cert': filename}
            check = AgentCheck('test', {}, [instance])
            context = check.get_tls_context()  # type: MagicMock
            context.load_verify_locations.assert_called_with(cafile=filename, capath=None, cadata=None)

    def test_ca_cert_dir(self):
        with patch('ssl.SSLContext'), TempDir("test_ca_cert_file") as tmp_dir:
            instance = {'tls_ca_cert': tmp_dir}
            check = AgentCheck('test', {}, [instance])
            context = check.get_tls_context()  # type: MagicMock
            context.load_verify_locations.assert_called_with(cafile=None, capath=tmp_dir, cadata=None)

    def test_ca_cert_expand_user(self):
        instance = {'tls_ca_cert': '~/foo'}
        check = AgentCheck('test', {}, [instance])
        with patch('ssl.SSLContext'), patch('os.path') as mock_path:
            check.get_tls_context()
            mock_path.expanduser.assert_called_with('~/foo')

    def test_client_cert_no_key_no_pass(self):
        instance = {'tls_cert': 'foo'}
        check = AgentCheck('test', {}, [instance])
        with patch('ssl.SSLContext'):
            context = check.get_tls_context()  # type: MagicMock
            context.load_cert_chain.assert_called_with('foo', keyfile=None, password=None)

    def test_client_cert_key_no_pass(self):
        instance = {'tls_cert': 'foo', 'tls_private_key': 'bar'}
        check = AgentCheck('test', {}, [instance])
        with patch('ssl.SSLContext'):
            context = check.get_tls_context()  # type: MagicMock
            context.load_cert_chain.assert_called_with('foo', keyfile='bar', password=None)

    def test_client_cert_key_and_pass(self):
        instance = {'tls_cert': 'foo', 'tls_private_key': 'bar', 'tls_private_key_password': 'pass'}
        check = AgentCheck('test', {}, [instance])
        with patch('ssl.SSLContext'):
            context = check.get_tls_context()  # type: MagicMock
            context.load_cert_chain.assert_called_with('foo', keyfile='bar', password='pass')

    def test_client_cert_expanded(self):
        instance = {'tls_cert': '~/foo'}
        check = AgentCheck('test', {}, [instance])
        with patch('ssl.SSLContext'), patch('os.path.expanduser') as mock_expand:
            check.get_tls_context()
            mock_expand.assert_called_with('~/foo')

    def test_client_key_expanded(self):
        instance = {'tls_private_key': '~/foo'}
        check = AgentCheck('test', {}, [instance])
        with patch('ssl.SSLContext'), patch('os.path.expanduser') as mock_expand:
            check.get_tls_context()
            mock_expand.assert_called_with('~/foo')


class TestTLSContextOverrides:
    def test_override_context(self):
        instance = {'tls_cert': 'foo', 'tls_private_key': 'bar'}
        check = AgentCheck('test', {}, [instance])

        overrides = {'tls_cert': 'not_foo'}
        with patch('ssl.SSLContext'):
            context = check.get_tls_context(overrides=overrides)  # type: MagicMock
            context.load_cert_chain.assert_called_with('not_foo', keyfile='bar', password=None)

    def test_override_context_empty(self):
        instance = {'tls_cert': 'foo', 'tls_private_key': 'bar'}
        check = AgentCheck('test', {}, [instance])

        overrides = {}
        with patch('ssl.SSLContext'):
            context = check.get_tls_context(overrides=overrides)  # type: MagicMock
            context.load_cert_chain.assert_called_with('foo', keyfile='bar', password=None)

    def test_override_context_wrapper_config(self):
        instance = {'tls_verify': True}
        overrides = {'tls_verify': False}
        tls = TlsContextWrapper(instance, overrides=overrides)
        assert tls.config['tls_verify'] is False

    def test_override_context_wrapper_config_empty(self):
        instance = {'tls_verify': True}
        overrides = {}
        tls = TlsContextWrapper(instance, overrides=overrides)
        assert tls.config['tls_verify'] is True
