# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for KerberosAuth and NTLMAuth httpx.Auth adapters.

All spnego calls are mocked so these tests run without any Kerberos/NTLM
infrastructure and without the spnego package itself being importable.
"""

import base64
from unittest.mock import MagicMock, call, patch

import httpx


def _make_response(status_code: int, headers: dict | None = None) -> httpx.Response:
    """Build a minimal httpx.Response for testing auth flows."""
    return httpx.Response(status_code, headers=headers or {})


def _run_auth_flow(auth: httpx.Auth, request: httpx.Request, responses: list[httpx.Response]) -> list[httpx.Request]:
    """Drive an auth_flow generator, feeding it successive responses.

    Returns the list of requests yielded by the flow.
    """
    gen = auth.auth_flow(request)
    sent_requests = []
    response_iter = iter(responses)
    try:
        req = next(gen)
        while True:
            sent_requests.append(req)
            try:
                resp = next(response_iter)
            except StopIteration:
                # No more responses — generator should stop after last yield
                break
            try:
                req = gen.send(resp)
            except StopIteration:
                break
    except StopIteration:
        pass
    return sent_requests


class TestKerberosAuth:
    def _make_mock_spnego(self, token: bytes = b'KERB-TOKEN') -> MagicMock:
        mock_spnego = MagicMock()
        ctx = MagicMock()
        ctx.step.return_value = token
        mock_spnego.ContextReq.sequence_detect = 1
        mock_spnego.ContextReq.delegate = 2
        mock_spnego.ContextReq.mutual_auth = 4
        mock_spnego.client.return_value = ctx
        mock_spnego.KerberosKeytab = MagicMock(return_value=MagicMock())
        mock_spnego.Credential = MagicMock(return_value=MagicMock())
        mock_spnego.CredentialCache = MagicMock(return_value=MagicMock())
        return mock_spnego, ctx

    def test_non_preemptive_sends_first_without_auth(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        mock_spnego, ctx = self._make_mock_spnego()

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=False)
            request = httpx.Request('GET', 'http://example.com/api')
            ok_response = _make_response(200)
            sent = _run_auth_flow(auth, request, [ok_response])

        # First request sent without any Authorization header
        assert len(sent) >= 1
        assert 'Authorization' not in sent[0].headers

    def test_non_preemptive_retries_with_negotiate_on_401(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        token_bytes = b'KERBTOKEN'
        mock_spnego, ctx = self._make_mock_spnego(token_bytes)

        # Encode server challenge token
        server_token = base64.b64encode(b'SERVER-CHALLENGE').decode()
        challenge_headers = {'www-authenticate': f'Negotiate {server_token}'}

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=False)
            request = httpx.Request('GET', 'http://example.com/api')
            responses = [_make_response(401, challenge_headers), _make_response(200)]
            sent = _run_auth_flow(auth, request, responses)

        assert len(sent) == 2
        # Second request must have the Negotiate header
        assert 'Authorization' in sent[1].headers
        auth_header = sent[1].headers['Authorization']
        assert auth_header.startswith('Negotiate ')
        # Verify the token in the header matches what ctx.step() returned
        decoded = base64.b64decode(auth_header.split(' ', 1)[1])
        assert decoded == token_bytes

    def test_force_preemptive_sends_token_immediately(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        token_bytes = b'PREEMPTTOKEN'
        mock_spnego, ctx = self._make_mock_spnego(token_bytes)

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=True)
            request = httpx.Request('GET', 'http://example.com/api')
            sent = _run_auth_flow(auth, request, [_make_response(200)])

        assert len(sent) >= 1
        assert 'Authorization' in sent[0].headers
        assert sent[0].headers['Authorization'].startswith('Negotiate ')

    def test_mutual_auth_calls_ctx_step_with_server_token(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        mock_spnego, ctx = self._make_mock_spnego(b'TOKEN')
        server_mutual_token = base64.b64encode(b'MUTUAL-TOKEN').decode()
        final_headers = {'www-authenticate': f'Negotiate {server_mutual_token}'}

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=True, mutual_authentication='required')
            request = httpx.Request('GET', 'http://example.com/')
            # Preemptive: first response has mutual auth token
            _run_auth_flow(auth, request, [_make_response(200, final_headers)])

        # ctx.step should be called at least twice: once for token, once for mutual auth
        assert ctx.step.call_count >= 2

    def test_mutual_auth_disabled_skips_verification(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        mock_spnego, ctx = self._make_mock_spnego(b'TOKEN')
        final_headers = {'www-authenticate': 'Negotiate SOMETOKEN'}

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=True, mutual_authentication='disabled')
            request = httpx.Request('GET', 'http://example.com/')
            _run_auth_flow(auth, request, [_make_response(200, final_headers)])

        # mutual_auth disabled — ctx.step called only once (for the initial token)
        assert ctx.step.call_count == 1

    def test_keytab_used_when_configured(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        mock_spnego, ctx = self._make_mock_spnego()

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=True, keytab='/path/to/keytab', principal='user@REALM')
            request = httpx.Request('GET', 'http://host.example.com/')
            _run_auth_flow(auth, request, [_make_response(200)])

        mock_spnego.KerberosKeytab.assert_called_once_with('/path/to/keytab', 'user@REALM')

    def test_delegate_flag_sets_context_req(self):
        from datadog_checks.base.utils.httpx_auth import KerberosAuth

        mock_spnego, ctx = self._make_mock_spnego()

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = KerberosAuth(force_preemptive=True, delegate=True)
            request = httpx.Request('GET', 'http://example.com/')
            _run_auth_flow(auth, request, [_make_response(200)])

        # Verify spnego.client was called with context_req that includes delegate flag
        call_kwargs = mock_spnego.client.call_args.kwargs
        # delegate bit (2) should be OR'd in
        assert call_kwargs['context_req'] & mock_spnego.ContextReq.delegate


class TestNTLMAuth:
    def _make_mock_spnego(self, type1: bytes = b'TYPE1', type3: bytes = b'TYPE3') -> tuple:
        mock_spnego = MagicMock()
        ctx = MagicMock()
        ctx.step.side_effect = [type1, type3]
        mock_spnego.NegotiateOptions.none = 0
        mock_spnego.NegotiateOptions.use_ntlm = 1
        mock_spnego.client.return_value = ctx
        return mock_spnego, ctx

    def test_sends_type1_negotiate_first(self):
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        type1_bytes = b'NTLM-TYPE1'
        mock_spnego, ctx = self._make_mock_spnego(type1=type1_bytes)

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = NTLMAuth('DOMAIN\\user', 'password')
            request = httpx.Request('GET', 'http://example.com/api')
            sent = _run_auth_flow(auth, request, [_make_response(200)])

        assert 'Authorization' in sent[0].headers
        auth_header = sent[0].headers['Authorization']
        assert auth_header.startswith('NTLM ')
        decoded = base64.b64decode(auth_header.split(' ', 1)[1])
        assert decoded == type1_bytes

    def test_completes_three_step_handshake(self):
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        type1_bytes = b'TYPE1'
        type3_bytes = b'TYPE3'
        mock_spnego, ctx = self._make_mock_spnego(type1_bytes, type3_bytes)

        challenge_b64 = base64.b64encode(b'NTLM-CHALLENGE').decode()
        challenge_headers = {'www-authenticate': f'NTLM {challenge_b64}'}

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = NTLMAuth('DOMAIN\\user', 'password')
            request = httpx.Request('GET', 'http://example.com/api')
            responses = [_make_response(401, challenge_headers), _make_response(200)]
            sent = _run_auth_flow(auth, request, responses)

        assert len(sent) == 2
        # Second request has Type 3 token
        auth_header3 = sent[1].headers['Authorization']
        assert auth_header3.startswith('NTLM ')
        decoded3 = base64.b64decode(auth_header3.split(' ', 1)[1])
        assert decoded3 == type3_bytes

        # ctx.step called with the challenge for Type 3
        step_calls = ctx.step.call_args_list
        assert len(step_calls) == 2
        assert step_calls[1] == call(in_token=b'NTLM-CHALLENGE')

    def test_stops_after_non_401(self):
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        mock_spnego, ctx = self._make_mock_spnego()

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = NTLMAuth('user', 'pass')
            request = httpx.Request('GET', 'http://example.com/api')
            sent = _run_auth_flow(auth, request, [_make_response(200)])

        # Only one request sent — no 401 retry needed
        assert len(sent) == 1

    def test_use_ntlm_option_set_with_credentials(self):
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        mock_spnego, ctx = self._make_mock_spnego()

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = NTLMAuth('user', 'pass')
            request = httpx.Request('GET', 'http://example.com/api')
            _run_auth_flow(auth, request, [_make_response(200)])

        call_kwargs = mock_spnego.client.call_args.kwargs
        assert call_kwargs['options'] == mock_spnego.NegotiateOptions.use_ntlm

    def test_no_credentials_uses_default_options(self):
        from datadog_checks.base.utils.httpx_auth import NTLMAuth

        mock_spnego, ctx = self._make_mock_spnego()

        with patch('datadog_checks.base.utils.httpx_auth.spnego', mock_spnego):
            auth = NTLMAuth(None, None)
            request = httpx.Request('GET', 'http://example.com/api')
            _run_auth_flow(auth, request, [_make_response(200)])

        call_kwargs = mock_spnego.client.call_args.kwargs
        assert call_kwargs['options'] == mock_spnego.NegotiateOptions.none
