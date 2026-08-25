from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Buffer


class Hash(Protocol):
    def digest(self) -> bytes: ...
    def hexdigest(self) -> str: ...
    def update(self, obj: Buffer, /) -> None: ...
    def copy(self) -> Hash: ...


class HashingAlgorithm(Protocol):
    def __call__(self, data: bytes, *args: Any, **kwargs: Any) -> Hash: ...


class HashMethod:
    """
    Singleton class used to provide hashing algorithms
    """

    _architecture: str | None = None
    _secure: HashingAlgorithm | None = None
    _fast: HashingAlgorithm | None = None

    @classmethod
    def secure(cls) -> HashingAlgorithm:
        """
        Provides a secure hashing algorithm.

        This algorithm is compliant with the FIPS 140-2 standard.
        """
        if cls._secure is not None:
            return cls._secure

        from hashlib import sha256

        def secure(data: bytes, *args: Any, **kwargs: Any) -> Hash:
            return sha256(data, *args, **kwargs)

        cls._secure = secure
        return cls._secure

    @classmethod
    def fast(cls) -> HashingAlgorithm:
        """
        Provides a fast hashing algorithm.

        If the platform is 64bit, it will use the blake2b algorithm, otherwise it will use the blake2s algorithm.
        """
        if cls._fast is not None:
            return cls._fast

        from hashlib import blake2b, blake2s

        selected_blake = blake2b if cls.architecture() == "64bit" else blake2s

        def blake(data: bytes, *args: Any, **kwargs: Any) -> Hash:
            return selected_blake(data, *args, **kwargs)

        cls._fast = blake
        return cls._fast

    @classmethod
    def architecture(cls) -> str:
        if cls._architecture is not None:
            return cls._architecture

        from datadog_checks.base.utils.platform import Platform

        cls._architecture = Platform().python_architecture()
        return cls._architecture
