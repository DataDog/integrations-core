# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from azure.identity import ManagedIdentityCredential

DEFAULT_PERMISSION_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


# Use the azure identity API to generate a token that will be used
# authenticate with either a system or user assigned managed identity
def generate_managed_identity_token(client_id: str, identity_scope: str = None):
    credential = ManagedIdentityCredential(client_id=client_id)
    if not identity_scope:
        identity_scope = DEFAULT_PERMISSION_SCOPE
    return credential.get_token(identity_scope).token
