from __future__ import annotations

try:
    import grpc

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False


# ---------------------------------------------------------------------------
# Protobuf encoder
# ---------------------------------------------------------------------------


def _encode_varint(value: int) -> bytes:
    parts = []
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            parts.append(byte | 0x80)
        else:
            parts.append(byte)
            break
    return bytes(parts)


def _ldelim_field(field_number: int, payload: bytes) -> bytes:
    """Encode a length-delimited (wire type 2) protobuf field."""
    tag = _encode_varint((field_number << 3) | 2)
    return tag + _encode_varint(len(payload)) + payload


def _string_field(field_number: int, value: str) -> bytes:
    return _ldelim_field(field_number, value.encode())


def _build_list_pod_sandbox_request(sandbox_id: str) -> bytes:
    """
    Encode a ListPodSandboxRequest with an exact ID filter.

    ListPodSandboxRequest { filter = 1: PodSandboxFilter { id = 1: string } }
    """
    filter_bytes = _string_field(1, sandbox_id)  # PodSandboxFilter.id
    return _ldelim_field(1, filter_bytes)  # ListPodSandboxRequest.filter


# ---------------------------------------------------------------------------
# Protobuf decoder
# ---------------------------------------------------------------------------


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7


def _parse_fields(data: bytes) -> dict[int, list[bytes]]:
    """Parse protobuf wire bytes into {field_number: [payload_bytes, ...]}."""
    fields: dict[int, list[bytes]] = {}
    pos = 0
    while pos < len(data):
        tag, pos = _decode_varint(data, pos)
        field_number = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 2:  # LEN
            length, pos = _decode_varint(data, pos)
            fields.setdefault(field_number, []).append(data[pos : pos + length])
            pos += length
        elif wire_type == 0:  # varint — skip
            _, pos = _decode_varint(data, pos)
        elif wire_type == 1:  # 64-bit fixed — skip
            pos += 8
        elif wire_type == 5:  # 32-bit fixed — skip
            pos += 4
        else:
            break  # unknown wire type; stop
    return fields


def _str(raw: bytes) -> str:
    return raw.decode('utf-8', errors='replace')


def _parse_sandbox_metadata(data: bytes) -> dict[str, str]:
    """PodSandboxMetadata: name=1, uid=2, namespace=3."""
    f = _parse_fields(data)
    return {
        'name': _str(f.get(1, [b''])[0]),
        'uid': _str(f.get(2, [b''])[0]),
        'namespace': _str(f.get(3, [b''])[0]),
    }


def _parse_list_pod_sandbox_response(data: bytes) -> list[dict[str, str]]:
    """
    ListPodSandboxResponse { items = 1: repeated PodSandbox }
    PodSandbox: id=1, metadata=2
    """
    result = []
    for item_bytes in _parse_fields(data).get(1, []):
        item_fields = _parse_fields(item_bytes)
        metadata: dict[str, str] = {}
        if 2 in item_fields:
            metadata = _parse_sandbox_metadata(item_fields[2][0])
        result.append(
            {
                'id': _str(item_fields.get(1, [b''])[0]),
                **metadata,
            }
        )
    return result


# ---------------------------------------------------------------------------
# CRI client
# ---------------------------------------------------------------------------

_LIST_POD_SANDBOX = '/runtime.v1.RuntimeService/ListPodSandbox'


class CRIClient:
    """Thin CRI gRPC client for resolving a sandbox ID to its Kubernetes pod UID."""

    DEFAULT_SOCKET = '/run/containerd/containerd.sock'

    def __init__(self, socket_path: str = DEFAULT_SOCKET, timeout: float = 5.0) -> None:
        if not GRPC_AVAILABLE:
            raise RuntimeError('grpcio is not installed; CRI enrichment is unavailable')
        self._timeout = timeout
        self._channel = grpc.insecure_channel('unix://' + socket_path)
        self._rpc = self._channel.unary_unary(
            _LIST_POD_SANDBOX,
            request_serializer=lambda b: b,
            response_deserializer=lambda b: b,
        )

    def get_pod_uid(self, sandbox_id: str) -> str | None:
        """Return the Kubernetes pod UID for *sandbox_id*, or None on any error."""
        try:
            response_bytes = self._rpc(
                _build_list_pod_sandbox_request(sandbox_id),
                timeout=self._timeout,
            )
        except Exception:
            return None

        sandboxes = _parse_list_pod_sandbox_response(response_bytes)
        if sandboxes:
            return sandboxes[0].get('uid') or None
        return None

    def close(self) -> None:
        self._channel.close()
