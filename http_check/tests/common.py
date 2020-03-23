# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))

MOCKBIN_URL = 'http://localhost:8080/request'

CONFIG = {
    'instances': [
        {
            'name': 'conn_error',
            'url': 'https://thereisnosuchlink.com',
            'check_certificate_expiration': False,
            'timeout': 1,
        },
        {
            'name': 'http_error_status_code',
            'url': 'https://valid.mock/404',
            'check_certificate_expiration': False,
            'timeout': 1,
        },
        {
            'name': 'status_code_match',
            'url': 'https://valid.mock/404',
            'http_response_status_code': '4..',
            'check_certificate_expiration': False,
            'timeout': 1,
            'tags': ["foo:bar"],
        },
        {
            'name': 'cnt_mismatch',
            'url': 'https://valid.mock/',
            'timeout': 1,
            'check_certificate_expiration': False,
            'content_match': 'thereisnosuchword',
        },
        {
            'name': 'cnt_match',
            'url': 'https://valid.mock/',
            'timeout': 1,
            'check_certificate_expiration': False,
            'content_match': '(thereisnosuchword|nginx)',
        },
        {
            'name': 'cnt_match_unicode',
            'url': 'https://valid.mock/unicode.html',
            'timeout': 1,
            'check_certificate_expiration': False,
            'content_match': u'œ∑ç√∫',
        },
        {
            'name': 'cnt_mismatch_unicode',
            'url': 'https://valid.mock/unicode.html',
            'timeout': 1,
            'check_certificate_expiration': False,
            'content_match': u'å∂œ∑√∂',
        },
        {
            'name': 'cnt_mismatch_reverse',
            'url': 'https://valid.mock',
            'timeout': 1,
            'reverse_content_match': True,
            'check_certificate_expiration': False,
            'content_match': 'thereisnosuchword',
        },
        {
            'name': 'cnt_match_reverse',
            'url': 'https://valid.mock',
            'timeout': 1,
            'reverse_content_match': True,
            'check_certificate_expiration': False,
            'content_match': '(thereisnosuchword|nginx)',
        },
        {
            'name': 'cnt_mismatch_unicode_reverse',
            'url': 'https://valid.mock/unicode.html',
            'timeout': 1,
            'reverse_content_match': True,
            'check_certificate_expiration': False,
            'content_match': u'å∂œ∑√∂',
        },
        {
            'name': 'cnt_match_unicode_reverse',
            'url': 'https://valid.mock/unicode.html',
            'timeout': 1,
            'reverse_content_match': True,
            'check_certificate_expiration': False,
            'content_match': u'œ∑ç√∫',
        },
    ]
}

CONFIG_E2E = {'init_config': {'ca_certs': '/opt/cacert.pem'}, 'instances': CONFIG['instances']}

CONFIG_SSL_ONLY = {
    'instances': [
        {
            'name': 'good_cert',
            'url': 'https://valid.mock:443',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 14,
            'days_critical': 7,
        },
        {
            'name': 'cert_exp_soon',
            'url': 'https://valid.mock',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 200,  # Just enough to trigger the warning alert
            'days_critical': 7,
        },
        {
            'name': 'cert_critical',
            'url': 'https://valid.mock',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 200,
            'days_critical': 200,  # Just enough to trigger the critical alert
        },
        {
            'name': 'conn_error',
            'url': 'https://thereisnosuchlink.com',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 14,
            'days_critical': 7,
        },
    ]
}

CONFIG_EXPIRED_SSL = {
    'instances': [
        {
            'name': 'expired_cert',
            'url': 'https://valid.mock',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 14,
            'days_critical': 7,
        },
        {
            'name': 'expired_cert_seconds',
            'url': 'https://valid.mock',
            'timeout': 1,
            'check_certificate_expiration': True,
            'seconds_warning': 3600,
            'seconds_critical': 60,
        },
    ]
}

CONFIG_CUSTOM_NAME = {
    'instances': [
        {
            'name': 'cert_validation_fails',
            'url': 'https://valid.mock:443',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 14,
            'days_critical': 7,
            'ssl_server_name': 'incorrect_name',
        },
        {
            'name': 'cert_validation_passes',
            'url': 'https://valid.mock:443',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 14,
            'days_critical': 7,
            'ssl_server_name': 'valid.mock',
        },
    ]
}

CONFIG_UNORMALIZED_INSTANCE_NAME = {
    'instances': [
        {
            'name': '_need-to__be_normalized-',
            'url': 'https://valid.mock',
            'timeout': 1,
            'check_certificate_expiration': True,
            'days_warning': 14,
            'days_critical': 7,
        }
    ]
}

CONFIG_DONT_CHECK_EXP = {
    'instances': [{'name': 'simple_config', 'url': 'https://expired.mock', 'check_certificate_expiration': False}]
}

CONFIG_HTTP_REDIRECTS = {
    'instances': [
        {
            'name': 'redirect_service',
            'url': 'https://valid.mock/301',
            'timeout': 1,
            'http_response_status_code': 301,
            'allow_redirects': False,
        }
    ]
}

FAKE_CERT = {'notAfter': 'Apr 12 12:00:00 2006 GMT'}

CONFIG_DATA_METHOD = {
    'instances': [
        {
            'name': 'post_json',
            'url': MOCKBIN_URL,
            'timeout': 1,
            'method': 'post',
            'data': {'foo': 'bar', 'baz': ['qux', 'quux']},
        },
        {
            'name': 'post_str',
            'url': MOCKBIN_URL,
            'timeout': 1,
            'method': 'post',
            'data': '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"'
            'xmlns:m="http://www.example.org/stocks"><soap:Header></soap:Header><soap:Body><m:GetStockPrice>'
            '<m:StockName>EXAMPLE</m:StockName></m:GetStockPrice></soap:Body></soap:Envelope>',
        },
        {
            'name': 'put_json',
            'url': MOCKBIN_URL,
            'timeout': 1,
            'method': 'put',
            'data': {'foo': 'bar', 'baz': ['qux', 'quux']},
        },
        {'name': 'put_str', 'url': MOCKBIN_URL, 'timeout': 1, 'method': 'put', 'data': 'Lorem ipsum'},
        {
            'name': 'patch_json',
            'url': MOCKBIN_URL,
            'timeout': 1,
            'method': 'patch',
            'data': {'foo': 'bar', 'baz': ['qux', 'quux']},
        },
        {'name': 'patch_str', 'url': MOCKBIN_URL, 'timeout': 1, 'method': 'patch', 'data': 'Lorem ipsum'},
        {
            'name': 'delete_json',
            'url': MOCKBIN_URL,
            'timeout': 1,
            'method': 'delete',
            'data': {'foo': 'bar', 'baz': ['qux', 'quux']},
        },
        {'name': 'delete_str', 'url': MOCKBIN_URL, 'timeout': 1, 'method': 'delete', 'data': 'Lorem ipsum'},
    ]
}
