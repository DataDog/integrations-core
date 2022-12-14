# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))

MOCKBIN_URL = "http://localhost:8080/request"

CONFIG = {
    "instances": [
        {
            "name": "conn_error",
            "url": "https://thereisnosuchlink.com",
            "check_certificate_expiration": False,
            "timeout": 1,
        },
        {
            "name": "http_error_status_code",
            "url": "https://valid.mock/404",
            "check_certificate_expiration": False,
            "timeout": 1,
        },
        {
            "name": "status_code_match",
            "url": "https://valid.mock/404",
            "http_response_status_code": "4..",
            "check_certificate_expiration": False,
            "timeout": 1,
            "tags": ["foo:bar"],
        },
        {
            "name": "cnt_mismatch",
            "url": "https://valid.mock/",
            "timeout": 1,
            "check_certificate_expiration": False,
            "content_match": "thereisnosuchword",
        },
        {
            "name": "cnt_match",
            "url": "https://valid.mock/",
            "timeout": 1,
            "check_certificate_expiration": False,
            "content_match": "(thereisnosuchword|nginx)",
        },
        {
            "name": "cnt_match_unicode",
            "url": "https://valid.mock/unicode.html",
            "timeout": 1,
            "check_certificate_expiration": False,
            "content_match": "œ∑ç√∫",
        },
        {
            "name": "cnt_mismatch_unicode",
            "url": "https://valid.mock/unicode.html",
            "timeout": 1,
            "check_certificate_expiration": False,
            "content_match": "å∂œ∑√∂",
        },
        {
            "name": "cnt_mismatch_reverse",
            "url": "https://valid.mock",
            "timeout": 1,
            "reverse_content_match": True,
            "check_certificate_expiration": False,
            "content_match": "thereisnosuchword",
        },
        {
            "name": "cnt_match_reverse",
            "url": "https://valid.mock",
            "timeout": 1,
            "reverse_content_match": True,
            "check_certificate_expiration": False,
            "content_match": "(thereisnosuchword|nginx)",
        },
        {
            "name": "cnt_mismatch_unicode_reverse",
            "url": "https://valid.mock/unicode.html",
            "timeout": 1,
            "reverse_content_match": True,
            "check_certificate_expiration": False,
            "content_match": "å∂œ∑√∂",
        },
        {
            "name": "cnt_match_unicode_reverse",
            "url": "https://valid.mock/unicode.html",
            "timeout": 1,
            "reverse_content_match": True,
            "check_certificate_expiration": False,
            "content_match": "œ∑ç√∫",
        },
    ]
}

CONFIG_E2E = {
    "init_config": {"ca_certs": "/opt/cacert.pem"},
    "instances": CONFIG["instances"],
}

CONFIG_SSL_ONLY = {
    "instances": [
        {
            "name": "good_cert",
            "url": "https://valid.mock:443",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 14,
            "days_critical": 7,
        },
        {
            "name": "cert_exp_soon",
            "url": "https://valid.mock",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 200,  # Just enough to trigger the warning alert
            "days_critical": 7,
        },
        {
            "name": "cert_critical",
            "url": "https://valid.mock",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 200,
            "days_critical": 200,  # Just enough to trigger the critical alert
        },
        {
            "name": "conn_error",
            "url": "https://thereisnosuchlink.com",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 14,
            "days_critical": 7,
        },
    ]
}

CONFIG_EXPIRED_SSL = {
    "instances": [
        {
            "name": "expired_cert",
            "url": "https://valid.mock",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 14,
            "days_critical": 7,
        },
        {
            "name": "expired_cert_seconds",
            "url": "https://valid.mock",
            "timeout": 1,
            "check_certificate_expiration": True,
            "seconds_warning": 3600,
            "seconds_critical": 60,
        },
    ]
}

CONFIG_CUSTOM_NAME = {
    "instances": [
        {
            "name": "cert_validation_fails",
            "url": "https://valid.mock:443",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 14,
            "days_critical": 7,
            "ssl_server_name": "incorrect_name",
        },
        {
            "name": "cert_validation_passes",
            "url": "https://valid.mock:443",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 14,
            "days_critical": 7,
            "ssl_server_name": "valid.mock",
        },
    ]
}

CONFIG_UNORMALIZED_INSTANCE_NAME = {
    "instances": [
        {
            "name": "_need-to__be_normalized-",
            "url": "https://valid.mock",
            "timeout": 1,
            "check_certificate_expiration": True,
            "days_warning": 14,
            "days_critical": 7,
        }
    ]
}

CONFIG_DONT_CHECK_EXP = {
    "instances": [
        {
            "name": "simple_config",
            "url": "https://expired.mock",
            "check_certificate_expiration": False,
        }
    ]
}

CONFIG_HTTP_NO_REDIRECTS = {
    "instances": [
        {
            "name": "no_allow_redirect_service",
            "url": "https://valid.mock/301",
            "timeout": 1,
            "http_response_status_code": 301,
            "allow_redirects": False,
        }
    ]
}

CONFIG_HTTP_ALLOW_REDIRECTS = {
    "instances": [
        {
            "name": "allow_redirect_service",
            "url": "https://valid.mock/301",
            "timeout": 1,
            "http_response_status_code": 200,
            "allow_redirects": True,
        }
    ]
}

FAKE_CERT = (
    b"0\x82\x05\xa60\x82\x03\x8e\xa0\x03\x02\x01\x02\x02\x08G "
    b"\x93\xeaI\x98\rS0\r\x06\t*\x86H\x86\xf7\r\x01\x01\x0b\x05\x000i1\x0b0\t\x06\x03U\x04\x06\x13\x02US1"
    b"\x0e0\x0c\x06\x03U\x04\x08\x0c\x05Texas1\x100\x0e\x06\x03U\x04\x07\x0c\x07Houston1\x180\x16\x06\x03U"
    b"\x04\n\x0c\x0fSSL Corporation1\x1e0\x1c\x06\x03U\x04\x03\x0c\x15SSL.com RSA SSL "
    b"subCA0\x1e\x17\r160801204830Z\x17\r160802204830Z0!1\x1f0\x1d\x06\x03U\x04\x03\x0c\x16expired-rsa-dv.ssl"
    b'.com0\x82\x01"0\r\x06\t*\x86H\x86\xf7\r\x01\x01\x01\x05\x00\x03\x82\x01\x0f\x000\x82\x01\n\x02\x82\x01'
    b"\x01\x00\x9a0:\x84zk\xd8\xfc\xcc\x8aX\xd6\xb6\xa8\xb8\x1d\xbc\xaat["
    b'\x0c\x8bz\x9b\xa4V>SB\x97M\x0b\x15\xa8\x8b\xaa\x15w6"\xbd\xe0*n&T\t\x92\xf0\xf33\xfciX\xb1\xf3\xa3\xfa'
    b"\x08cfQ(V\x07T\xffb\x8b\xc5y\x7f\xaej\xd6\xe3\xa1\x80\xc4l\xf7}\xa4\xb9\x9c\x11zU\xea\x7f\xdd\xfc\r"
    b";\x1fn{\xfa\x84\xa7\xf5\x03\xc1\xee\xe5\x90K.\x90M\x9b\xea|p\xd6\xcf\xc2\xc5\xc3\xb4\x95lB\xfdKOINo\xbe"
    b"\xf5P\xd0d\xe0q$?\xf8\xc9n\x8bf\xd2\x1b\\\xd9\x07w\xb3,"
    b"\xf2\xe1P\xa4Z\x92\x19q\xa3\x13C\xdf.@\n\x84\xf2\xa9/+\xde\x9f\xeaC\xbb\x84\xdb\xd9\xb9-T\t\x03p\xef"
    b'\xc5\xaf^.\xb4/\xf2\x0e\x9e\x1b\x04\x8c\x03\xef\xf5G)"\x03\x80\x10M\xc9Sv]\x10\x0e\xbbf|K\xf6\x1a*\x1b'
    b'\xee\x84\xb5\xe1\x8f\x9a\x81\r\xef\x9co\xf0\xef\x814\xfaX\x86\xab"q\x1e\xa5c\x1aP1\x14\x1f5FIw9\x02\x03'
    b"\x01\x00\x01\xa3\x82\x01\x980\x82\x01\x940\x1f\x06\x03U\x1d#\x04\x180\x16\x80\x14&\x14~\xe0\xdc\xd7\xa6"
    b"\xf7\xe2\xd4\x04'\xdfa\xf1\xc2\xec\xe72\xca0q\x06\x08+\x06\x01\x05\x05\x07\x01\x01\x04e0c0?\x06\x08"
    b"+\x06\x01\x05\x05\x070\x02\x863http://www.ssl.com/repository/SSLcomRSASSLsubCA.cer0 "
    b"\x06\x08+\x06\x01\x05\x05\x070\x01\x86\x14http://ocsps.ssl.com0!\x06\x03U\x1d\x11\x04\x1a0\x18\x82"
    b"\x16expired-rsa-dv.ssl.com0Q\x06\x03U\x1d \x04J0H0<\x06\x0c+\x06\x01\x04\x01\x82\xa90\x01\x01\x01\x000,"
    b"0*\x06\x08+\x06\x01\x05\x05\x07\x02\x01\x16\x1ehttps://www.ssl.com/repository0\x08\x06\x06g\x81\x0c\x01"
    b"\x02\x010\x1d\x06\x03U\x1d%\x04\x160\x14\x06\x08+\x06\x01\x05\x05\x07\x03\x02\x06\x08+\x06\x01\x05\x05"
    b"\x07\x03\x010:\x06\x03U\x1d\x1f\x043010/\xa0-\xa0+\x86)http://crls.ssl.com/SSLcomRSASSLsubCA.crl0\x1d"
    b"\x06\x03U\x1d\x0e\x04\x16\x04\x14c\xe02\xe0\xea\xad=\x84m\xe3\xe9{"
    b"\x95z\xd8\x96\xa8;\xd8<0\x0e\x06\x03U\x1d\x0f\x01\x01\xff\x04\x04\x03\x02\x05\xa00\r\x06\t*\x86H\x86"
    b"\xf7\r\x01\x01\x0b\x05\x00\x03\x82\x02\x01\x00Ez\xddH\x0e\xb1\xf1\\\xa8\xf4\x8f\x81('\xef\xc1zY,"
    b"\x8f\x87i@\x00\xc6\xbb\x03\xc4\xd8S\xb1Y\xe4\xe2\x05G\xde\xdcfvs\xa3\x9bf?G\x91\x93\xa1_\xce\xba\xf1"
    b"%\xb0u<\xf6\xad\x81\xf8\x8b'\x95r)\x14o-\xee\xcc\xed\xefIL\xf0\x8f\x91\x92\xf5Qg\xa6\x9e\x174\x94:\x9b"
    b"\xb9M\xde\xd7\x8b\xf0\xdd-Wg\xdeL "
    b"ka\xf2E\xc76\xf3\xa3\xe4\x17\xac>\xeb2%\xf5c\xd1\xa02\xe1\xb1\xa0l%\xc9\xc5r0\x8d8x8\xb8\xa8\xe4\x9b"
    b"\xecc\xab\xcc|\xea\x8e\xd1i\x1b\x9f\x0e\xc9\x17\x1c'("
    b"\xe6x\x81\x83\xd9\xc5o\x19E@\xecH\x88\x8dm\xd9\x1d\x8dK\xafa\xec\x1e\xfa\xc9\x1a\x10\x92\xf9\x87\xa9"
    b'\xaf[\xdb\xd4\xb4\x955"\xba\xcf\xd8\xab\x0f\xadt4\xa9\xc3\x9dUVO\xc3\x00\xe1\x99\x98\xd8\xc8\x972\xf4Oj'
    b'\x16\x9fn\x8d\x95_-\xec4\x93\xaf"\xaeX\t\xe3\x16T\xd4\x06f\x12\nRg\xd6L\xf3\xb0\xa7<\x96\xfevLN\x9a\xe7'
    b"\x1bJ\xba\x0c\xa0\x9f\xca\x93\x0c\x0b9dh\xb2\xbe\x8be\xc2>2c\xc8\xb2\xf8*\x80\xac\xfa\x16d\xb3h`u\x0f"
    b"*\xcd\xd8\x94\xc8{\x91\x9b}\x0b\xf22~\xab\xc6\xcf@D^\xf4\xa2\x85\x05\xa2\xaexf\xe3\x88\xbeZ`=\xec\x80"
    b"\xc7\xfd\xc0.\x0b\xb8\x9f==\x0b\t\xf9\x12\x94\xedQ\xc5\xa5\\\\\x1f]I\x04\xf9\xe5D\x07\x05\xa9\xe09\xc6q"
    b"\n\xa6y\x07\xa1\x01H\x82\x0c\xc9\xf2\t\rF\xea\x82!oU\x02-\xa3(\xd18\x05\xe8\xa4\xf4o("
    b"\xa6\xbeV\x0c\x0c\xda\xa5*\xcb2\xa2'9\xbdC\x08\xf2\xcc\x84\x98\x90\xa4qi>\xda\xd2\xa7\xc3\xcac\xb7\xd4"
    b"\xf6r\xfc\xfe\x94_[K\xcd?\xe9\xedtjf\xde\x9d}\xb1\xdb\xea\xb2\xf7\xa4U\x9bb\xed\xf5\x82\rE_#\x12s)\x8d3"
    b'\x92S\x07\x04\xa9\xf4\xff\xb0\xe9\xdc\xb2\xcb+}\x0c\x8b"B\xb4\x18l!*s\xfc\x84\xeccz\x08;o)\xed\x9a\xadb'
    b"\xddB*\xb24r\x08\x82\x95"
)

CONFIG_DATA_METHOD = {
    "instances": [
        {
            "name": "post_json",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "post",
            "data": {"foo": "bar", "baz": ["qux", "quux"]},
        },
        {
            "name": "post_str",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "post",
            "data": '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"'
            'xmlns:m="http://www.example.org/stocks"><soap:Header></soap:Header><soap:Body><m:GetStockPrice>'
            "<m:StockName>EXAMPLE</m:StockName></m:GetStockPrice></soap:Body></soap:Envelope>",
        },
        {
            "name": "put_json",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "put",
            "data": {"foo": "bar", "baz": ["qux", "quux"]},
        },
        {
            "name": "put_str",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "put",
            "data": "Lorem ipsum",
        },
        {
            "name": "patch_json",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "patch",
            "data": {"foo": "bar", "baz": ["qux", "quux"]},
        },
        {
            "name": "patch_str",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "patch",
            "data": "Lorem ipsum",
        },
        {
            "name": "delete_json",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "delete",
            "data": {"foo": "bar", "baz": ["qux", "quux"]},
        },
        {
            "name": "delete_str",
            "url": MOCKBIN_URL,
            "timeout": 1,
            "method": "delete",
            "data": "Lorem ipsum",
        },
    ]
}
