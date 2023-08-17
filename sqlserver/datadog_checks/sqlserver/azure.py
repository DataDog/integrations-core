# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import struct

from azure.identity import ManagedIdentityCredential

DEFAULT_PERMISSION_SCOPE = "https://database.windows.net/.default"
TOKEN_ENCODING = "UTF-16-LE"


# Use the azure identity API to generate a token that will be used
# authenticate with either a system or user assigned managed identity
def generate_managed_identity_token(client_id: str, identity_scope: str = None):
    credential = ManagedIdentityCredential(client_id=client_id)
    if not identity_scope:
        identity_scope = DEFAULT_PERMISSION_SCOPE
    token_bytes = credential.get_token(identity_scope).token.encode(TOKEN_ENCODING)
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)

    return token_struct
