# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.http import RequestsWrapper

from .common import DEFAULT_OPTIONS, make_mock_session


def test_get():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.get('https://www.google.com')
    mock_session.get.assert_called_once_with('https://www.google.com', **http.options)


def test_get_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.get('https://www.google.com')
    mock_session.get.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_get_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.get('https://www.google.com', auth=options['auth'])
    mock_session.get.assert_called_once_with('https://www.google.com', **options)


def test_get_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.get('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.get.assert_called_once_with('https://www.google.com', **options)


def test_post():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.post('https://www.google.com')
    mock_session.post.assert_called_once_with('https://www.google.com', **http.options)


def test_post_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.post('https://www.google.com')
    mock_session.post.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_post_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.post('https://www.google.com', auth=options['auth'])
    mock_session.post.assert_called_once_with('https://www.google.com', **options)


def test_post_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.post('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.post.assert_called_once_with('https://www.google.com', **options)


def test_head():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.head('https://www.google.com')
    mock_session.head.assert_called_once_with('https://www.google.com', **http.options)


def test_head_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.head('https://www.google.com')
    mock_session.head.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_head_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.head('https://www.google.com', auth=options['auth'])
    mock_session.head.assert_called_once_with('https://www.google.com', **options)


def test_head_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.head('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.head.assert_called_once_with('https://www.google.com', **options)


def test_put():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.put('https://www.google.com')
    mock_session.put.assert_called_once_with('https://www.google.com', **http.options)


def test_put_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.put('https://www.google.com')
    mock_session.put.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_put_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.put('https://www.google.com', auth=options['auth'])
    mock_session.put.assert_called_once_with('https://www.google.com', **options)


def test_put_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.put('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.put.assert_called_once_with('https://www.google.com', **options)


def test_patch():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.patch('https://www.google.com')
    mock_session.patch.assert_called_once_with('https://www.google.com', **http.options)


def test_patch_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.patch('https://www.google.com')
    mock_session.patch.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_patch_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.patch('https://www.google.com', auth=options['auth'])
    mock_session.patch.assert_called_once_with('https://www.google.com', **options)


def test_patch_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.patch('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.patch.assert_called_once_with('https://www.google.com', **options)


def test_delete():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.delete('https://www.google.com')
    mock_session.delete.assert_called_once_with('https://www.google.com', **http.options)


def test_delete_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.delete('https://www.google.com')
    mock_session.delete.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_delete_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.delete('https://www.google.com', auth=options['auth'])
    mock_session.delete.assert_called_once_with('https://www.google.com', **options)


def test_delete_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.delete('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.delete.assert_called_once_with('https://www.google.com', **options)


def test_options():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    http.options_method('https://www.google.com')
    mock_session.options.assert_called_once_with('https://www.google.com', **http.options)


def test_options_session():
    mock_session = make_mock_session()
    http = RequestsWrapper({'persist_connections': True}, {}, session=mock_session)
    http.options_method('https://www.google.com')
    mock_session.options.assert_called_once_with('https://www.google.com', **DEFAULT_OPTIONS)


def test_options_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = http.options.copy()
    options['auth'] = ('user', 'pass')
    http.options_method('https://www.google.com', auth=options['auth'])
    mock_session.options.assert_called_once_with('https://www.google.com', **options)


def test_options_session_option_override():
    mock_session = make_mock_session()
    http = RequestsWrapper({}, {}, session=mock_session)
    options = DEFAULT_OPTIONS.copy()
    options.update({'auth': ('user', 'pass')})
    http.options_method('https://www.google.com', persist=True, auth=options['auth'])
    mock_session.options.assert_called_once_with('https://www.google.com', **options)
