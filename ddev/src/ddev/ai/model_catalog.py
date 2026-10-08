# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ANTHROPIC: Final = "anthropic"
ANTHROPIC_MESSAGES: Final = "anthropic-messages"

# Catalog data cannot grant an adapter support for a new protocol.
PROVIDER_PROTOCOLS: Final[dict[str, frozenset[str]]] = {ANTHROPIC: frozenset({ANTHROPIC_MESSAGES})}

SHIPPED_CATALOG: Final[Path] = Path(__file__).parent / "model_catalog.yaml"


class Route(StrEnum):
    """Where requests for a resolved model are sent."""

    DIRECT = "direct"
    AI_GATEWAY = "ai-gateway"


class BindingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: str = Field(min_length=1)
    model: str = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)


class PricingConfig(BaseModel):
    """Provider list-price estimates, USD per million tokens.

    A missing rate means the price is unknown, not free; zero is a valid known price.
    """

    model_config = ConfigDict(extra="forbid")

    input_usd_per_million: Decimal | None = Field(default=None, ge=0)
    output_usd_per_million: Decimal | None = Field(default=None, ge=0)
    cache_read_usd_per_million: Decimal | None = Field(default=None, ge=0)
    cache_write_5m_usd_per_million: Decimal | None = Field(default=None, ge=0)
    cache_write_1h_usd_per_million: Decimal | None = Field(default=None, ge=0)


class ModelConfig(BaseModel):
    """One canonical model.

    `context_window` is the real capacity of the model; bindings carry any headers needed to get it.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    context_window: int = Field(gt=0, strict=True)
    max_input_tokens: int | None = Field(default=None, gt=0, strict=True)
    max_output_tokens: int | None = Field(default=None, gt=0, strict=True)
    pricing: PricingConfig | None = None
    bindings: dict[Route, BindingConfig] = Field(min_length=1)


class CatalogConfig(BaseModel):
    """The validated shape of a model catalog file."""

    model_config = ConfigDict(extra="forbid")

    models: dict[str, ModelConfig]
    aliases: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_catalog(self) -> CatalogConfig:
        for name, spec in self.models.items():
            if name != name.lower():
                raise ValueError(f"Canonical model names must be lowercase: {name!r}")
            supported = PROVIDER_PROTOCOLS.get(spec.provider, frozenset())
            for binding in spec.bindings.values():
                if binding.protocol not in supported:
                    raise ValueError(
                        f"Model {name!r} binds protocol {binding.protocol!r} for provider "
                        f"{spec.provider!r}, which supports: {', '.join(sorted(supported)) or 'none'}"
                    )
            if spec.max_input_tokens is not None and spec.max_input_tokens > spec.context_window:
                raise ValueError(
                    f"Model {name!r} declares {spec.max_input_tokens} max input tokens above its "
                    f"{spec.context_window}-token context window"
                )
        seen: set[str] = set()
        for alias, target in self.aliases.items():
            key = alias.lower()
            if key in seen:
                raise ValueError(f"Aliases must be unique ignoring case: {alias!r}")
            seen.add(key)
            if key in self.models:
                raise ValueError(f"Alias {alias!r} conflicts with a canonical model name")
            if target not in self.models:
                raise ValueError(f"Model alias {alias!r} points at unknown model {target!r}")
        return self


@dataclass(frozen=True)
class ResolvedModel:
    canonical: str
    route: Route
    model: ModelConfig
    binding: BindingConfig

    def expected_cost(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_5m_tokens: int = 0,
        cache_write_1h_tokens: int = 0,
    ) -> Decimal | None:
        """Estimate one request's token cost in USD at the catalog's list prices.

        Counts are separate, non-overlapping usage buckets; `input_tokens` is uncached input,
        not total input. Returns None when pricing is missing or a used bucket's rate is
        unknown, so a partial total is never reported. The per-request total is not rounded.
        """
        if min(input_tokens, output_tokens, cache_read_tokens, cache_write_5m_tokens, cache_write_1h_tokens) < 0:
            raise ValueError("Token counts must be non-negative")
        pricing = self.model.pricing
        if pricing is None:
            return None
        counts = (
            (input_tokens, pricing.input_usd_per_million),
            (output_tokens, pricing.output_usd_per_million),
            (cache_read_tokens, pricing.cache_read_usd_per_million),
            (cache_write_5m_tokens, pricing.cache_write_5m_usd_per_million),
            (cache_write_1h_tokens, pricing.cache_write_1h_usd_per_million),
        )
        total = Decimal(0)
        for count, rate in counts:
            if count == 0:
                continue
            if rate is None:
                return None
            total += count * rate
        return total / 1_000_000


class ModelResolver:
    """Captures a catalog at construction and resolves names to route bindings."""

    def __init__(self, path: str | Path):
        resolved_path = Path(path).expanduser().resolve()
        try:
            data = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            raise ValueError(f"Could not read model catalog {resolved_path}: {error}") from error
        except yaml.YAMLError as error:
            raise ValueError(f"Model catalog {resolved_path} is not valid YAML: {error}") from error
        try:
            catalog = CatalogConfig.model_validate(data)
        except ValidationError as error:
            raise ValueError(f"Invalid model catalog {resolved_path}:\n{str(error).strip()}") from error
        self._models = catalog.models
        self._aliases = {alias.lower(): target for alias, target in catalog.aliases.items()}

    def names(self) -> frozenset[str]:
        """Every accepted name: aliases and canonical models."""
        return frozenset((*self._aliases, *self._models))

    def names_for(self, provider: str) -> frozenset[str]:
        """Accepted names whose canonical models belong to one provider."""
        owned = {name for name, spec in self._models.items() if spec.provider == provider}
        aliases = {alias for alias, target in self._aliases.items() if target in owned}
        return frozenset(owned | aliases)

    def resolve(self, name: str, *, route: Route, provider: str | None = None) -> ResolvedModel:
        canonical = self._canonical(name)
        spec = self._models[canonical]
        if provider is not None and spec.provider != provider:
            raise ValueError(f"Model {canonical!r} belongs to provider {spec.provider!r}, not {provider!r}")
        binding = spec.bindings.get(route)
        if binding is None:
            available = ", ".join(sorted(available.value for available in spec.bindings))
            raise ValueError(f"Model {canonical!r} has no {route.value!r} binding; available routes: {available}")
        return ResolvedModel(canonical=canonical, route=route, model=spec, binding=binding)

    def _canonical(self, name: str) -> str:
        key = name.lower()
        if key in self._aliases:
            return self._aliases[key]
        if key in self._models:
            return key
        raise ValueError(f"Unknown model {name!r}. Valid models: {', '.join(sorted(self.names()))}")


RESOLVER: Final[ModelResolver] = ModelResolver(SHIPPED_CATALOG)
