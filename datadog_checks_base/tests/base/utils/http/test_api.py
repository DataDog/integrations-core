# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import requests

from datadog_checks.base.utils.http import RequestsWrapper

from .common import DEFAULT_OPTIONS


def test_get():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.get'):
        http.get('https://www.google.com')
        requests.get.assert_called_once_with('https://www.google.com', **http.options)


def test_get_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.get('https://www.google.com')
        http.session.get.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_get_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.get'):
        http.get('https://www.google.com', auth=options['auth'])
        requests.get.assert_called_once_with('https://www.google.com', **options)


def test_get_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.get('https://www.google.com', persist=True, auth=options['auth'])
        http.session.get.assert_called_once_with('https://www.google.com', **options)


def test_post():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.post'):
        http.post('https://www.google.com')
        requests.post.assert_called_once_with('https://www.google.com', **http.options)


def test_post_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.post('https://www.google.com')
        http.session.post.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_post_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.post'):
        http.post('https://www.google.com', auth=options['auth'])
        requests.post.assert_called_once_with('https://www.google.com', **options)


def test_post_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.post('https://www.google.com', persist=True, auth=options['auth'])
        http.session.post.assert_called_once_with('https://www.google.com', **options)


def test_head():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.head'):
        http.head('https://www.google.com')
        requests.head.assert_called_once_with('https://www.google.com', **http.options)


def test_head_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.head('https://www.google.com')
        http.session.head.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_head_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.head'):
        http.head('https://www.google.com', auth=options['auth'])
        requests.head.assert_called_once_with('https://www.google.com', **options)


def test_head_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.head('https://www.google.com', persist=True, auth=options['auth'])
        http.session.head.assert_called_once_with('https://www.google.com', **options)


def test_put():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.put'):
        http.put('https://www.google.com')
        requests.put.assert_called_once_with('https://www.google.com', **http.options)


def test_put_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.put('https://www.google.com')
        http.session.put.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_put_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.put'):
        http.put('https://www.google.com', auth=options['auth'])
        requests.put.assert_called_once_with('https://www.google.com', **options)


def test_put_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.put('https://www.google.com', persist=True, auth=options['auth'])
        http.session.put.assert_called_once_with('https://www.google.com', **options)


def test_patch():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.patch'):
        http.patch('https://www.google.com')
        requests.patch.assert_called_once_with('https://www.google.com', **http.options)


def test_patch_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.patch('https://www.google.com')
        http.session.patch.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_patch_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.patch'):
        http.patch('https://www.google.com', auth=options['auth'])
        requests.patch.assert_called_once_with('https://www.google.com', **options)


def test_patch_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.patch('https://www.google.com', persist=True, auth=options['auth'])
        http.session.patch.assert_called_once_with('https://www.google.com', **options)


def test_delete():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.delete'):
        http.delete('https://www.google.com')
        requests.delete.assert_called_once_with('https://www.google.com', **http.options)


def test_delete_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.delete('https://www.google.com')
        http.session.delete.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_delete_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.delete'):
        http.delete('https://www.google.com', auth=options['auth'])
        requests.delete.assert_called_once_with('https://www.google.com', **options)


def test_delete_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.delete('https://www.google.com', persist=True, auth=options['auth'])
        http.session.delete.assert_called_once_with('https://www.google.com', **options)


def test_options():
    http = RequestsWrapper({}, {})

    with mock.patch('requests.options'):
        http.options_method('https://www.google.com')
        requests.options.assert_called_once_with('https://www.google.com', **http.options)


def test_options_session():
    http = RequestsWrapper({'persist_connections': True}, {})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.options_method('https://www.google.com')
        http.session.options.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_options_option_override():
    http = RequestsWrapper({}, {})
    options = http.options.copy()
    options['auth'] = ('user', 'pass')

    with mock.patch('requests.options'):
        http.options_method('https://www.google.com', auth=options['auth'])
        requests.options.assert_called_once_with('https://www.google.com', **options)


def test_options_session_option_override():
    http = RequestsWrapper({}, {})
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})

    with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.session'):
        http.options_method('https://www.google.com', persist=True, auth=options['auth'])
        http.session.options.assert_called_once_with('https://www.google.com', **options)
