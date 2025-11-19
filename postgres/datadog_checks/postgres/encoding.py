# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import List


def decode_with_encodings(byte_array: bytes, encodings: List[str]) -> str:
    encodings = encodings or ['utf-8']
    # Try strict mode first, then fallback to 'backslashreplace' if strict fails
    # This can happen if a statetment is truncated in the middle of a multibyte character
    for mode in ['strict', 'backslashreplace']:
        for encoding in encodings:
            try:
                return byte_array.decode(encoding, mode)
            except Exception:
                continue
    raise ValueError("No valid encoding found for the given byte array.")
