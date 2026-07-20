# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from azure.core.credentials import AccessToken
from azure.identity import ManagedIdentityCredential, WorkloadIdentityCredential

DEFAULT_PERMISSION_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"

AZURE_AUTH_TYPES = ('managed_identity', 'workload_identity')
AZURE_DEFAULT_AUTH_TYPE = 'managed_identity'


def generate_azure_token(
    auth_type: str,
    client_id: str | None = None,
    tenant_id: str | None = None,
    identity_scope: str | None = None,
) -> AccessToken:
    if auth_type == 'workload_identity':
        credential = WorkloadIdentityCredential(client_id=client_id, tenant_id=tenant_id)
    else:
        credential = ManagedIdentityCredential(client_id=client_id)
    return credential.get_token(identity_scope or DEFAULT_PERMISSION_SCOPE)
