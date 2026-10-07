# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from decimal import Decimal
from operator import delitem, setitem
from pathlib import Path
from re import escape

import pytest
import yaml

from ddev.ai.model_catalog import (
    ANTHROPIC,
    ANTHROPIC_MESSAGES,
    SHIPPED_CATALOG,
    BindingConfig,
    ModelConfig,
    ModelResolver,
    PricingConfig,
    ResolvedModel,
    Route,
)


def make_entry(
    *,
    provider: str = "anthropic",
    context_window: int = 1_000_000,
    max_input_tokens: int | None = None,
    max_output_tokens: int | None = None,
    pricing: PricingConfig | None = None,
    bindings: dict[Route, BindingConfig] | None = None,
) -> ModelConfig:
    return ModelConfig(
        provider=provider,
        context_window=context_window,
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
        pricing=pricing,
        bindings=bindings if bindings is not None else both_routes(),
    )


def both_routes(
    wire_model: str = "claude-opus-5-5", headers: dict[str, str] | None = None
) -> dict[Route, BindingConfig]:
    return {
        Route.DIRECT: BindingConfig(protocol=ANTHROPIC_MESSAGES, model=wire_model, headers=headers or {}),
        Route.AI_GATEWAY: BindingConfig(
            protocol=ANTHROPIC_MESSAGES, model=f"anthropic/{wire_model}", headers=headers or {}
        ),
    }


def make_resolver(tmp_path: Path, *, aliases: dict[str, str] | None = None, **entries: ModelConfig) -> ModelResolver:
    data = {
        "models": {name: entry.model_dump(mode="json") for name, entry in entries.items()},
        "aliases": aliases or {},
    }
    return ModelResolver(write_catalog(tmp_path / "catalog.yaml", yaml.safe_dump(data)))


def write_catalog(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return str(path)


MINIMAL_CATALOG = """\
models:
  fixture-model:
    provider: anthropic
    context_window: 100000
    bindings:
      direct:
        protocol: anthropic-messages
        model: fixture-model
"""

LONG_CONTEXT_CATALOG = """\
models:
  fixture-model:
    provider: anthropic
    context_window: 200000
    max_input_tokens: 200000
    max_output_tokens: 64000
    bindings:
      direct:
        protocol: anthropic-messages
        model: fixture-model
  fixture-model-1m:
    provider: anthropic
    context_window: 1000000
    max_input_tokens: 1000000
    max_output_tokens: 64000
    bindings:
      direct:
        protocol: anthropic-messages
        model: fixture-model
        headers:
          anthropic-beta: context-1m-2025-08-07
"""


SHIPPED_DATA = yaml.safe_load(SHIPPED_CATALOG.read_text(encoding="utf-8"))


@pytest.mark.parametrize("route", [Route.DIRECT, Route.AI_GATEWAY])
@pytest.mark.parametrize("name", sorted(SHIPPED_DATA["models"]))
def test_shipped_catalog_resolves_every_canonical_name_on_both_routes(name: str, route: Route):
    resolved = ModelResolver().resolve(name, route=route, provider=ANTHROPIC)

    assert resolved.canonical == name
    assert resolved.binding.model == SHIPPED_DATA["models"][name]["bindings"][route.value]["model"]


@pytest.mark.parametrize("alias", sorted(SHIPPED_DATA["aliases"]))
def test_shipped_aliases_resolve_to_their_declared_targets(alias: str):
    resolver = ModelResolver()
    target = SHIPPED_DATA["aliases"][alias]

    for route in Route:
        assert resolver.resolve(alias, route=route, provider=ANTHROPIC).canonical == target


def test_shipped_catalog_names_are_all_served_by_anthropic():
    resolver = ModelResolver()

    assert resolver.names_for(ANTHROPIC) == frozenset((*SHIPPED_DATA["aliases"], *SHIPPED_DATA["models"]))


FULL_PRICING = PricingConfig(
    input_usd_per_million="2",
    output_usd_per_million="10",
    cache_read_usd_per_million="0.10",
    cache_write_5m_usd_per_million="2.50",
    cache_write_1h_usd_per_million="4",
)


def make_resolved(pricing: PricingConfig | None = FULL_PRICING) -> ResolvedModel:
    spec = make_entry(pricing=pricing)
    return ResolvedModel(
        canonical="fixture-model",
        route=Route.DIRECT,
        model=spec,
        binding=spec.bindings[Route.DIRECT],
    )


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        pytest.param({"input_tokens": 0, "output_tokens": 0}, Decimal("0"), id="zero_usage"),
        pytest.param({"input_tokens": 1_000_000, "output_tokens": 0}, Decimal("2"), id="input_only"),
        pytest.param({"input_tokens": 333_333, "output_tokens": 0}, Decimal("0.666666"), id="not_rounded_to_cents"),
        pytest.param(
            {
                "input_tokens": 250_000,
                "output_tokens": 100_000,
                "cache_read_tokens": 500_000,
                "cache_write_5m_tokens": 200_000,
                "cache_write_1h_tokens": 100_000,
            },
            Decimal("2.45"),
            id="all_buckets_at_their_own_rates",
        ),
    ],
)
def test_expected_cost_sums_each_bucket_at_its_own_rate(counts: dict[str, int], expected: Decimal):
    assert make_resolved().expected_cost(**counts) == expected


def test_expected_cost_treats_zero_as_a_known_free_rate():
    free = PricingConfig(input_usd_per_million="0", output_usd_per_million="0")

    assert make_resolved(free).expected_cost(input_tokens=1_000_000, output_tokens=1_000_000) == Decimal("0")


def test_expected_cost_is_none_without_pricing():
    assert make_resolved(pricing=None).expected_cost(input_tokens=1_000_000, output_tokens=1_000_000) is None


def test_expected_cost_is_none_when_a_used_bucket_rate_is_unknown():
    partial = PricingConfig(input_usd_per_million="2", output_usd_per_million="10")

    assert make_resolved(partial).expected_cost(input_tokens=10, output_tokens=0, cache_read_tokens=10) is None


def test_expected_cost_ignores_unknown_rates_for_unused_buckets():
    partial = PricingConfig(input_usd_per_million="2", output_usd_per_million="10")

    assert make_resolved(partial).expected_cost(input_tokens=1_000_000, output_tokens=0) == Decimal("2")


@pytest.mark.parametrize("pricing", [None, FULL_PRICING], ids=["unpriced", "priced"])
@pytest.mark.parametrize(
    "counts",
    [
        {"input_tokens": -1, "output_tokens": 0},
        {"input_tokens": 0, "output_tokens": -1},
        {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": -1},
        {"input_tokens": 0, "output_tokens": 0, "cache_write_5m_tokens": -1},
        {"input_tokens": 0, "output_tokens": 0, "cache_write_1h_tokens": -1},
    ],
    ids=["input", "output", "cache_read", "cache_write_5m", "cache_write_1h"],
)
def test_expected_cost_rejects_negative_counts(counts: dict[str, int], pricing: PricingConfig | None):
    with pytest.raises(ValueError, match="non-negative"):
        make_resolved(pricing).expected_cost(**counts)


@pytest.mark.parametrize(
    ("mutate", "headers"),
    [
        pytest.param(lambda model: setattr(model.model, "context_window", 10), None, id="context_window"),
        pytest.param(
            lambda model: setattr(model.model.pricing, "input_usd_per_million", Decimal("50")),
            None,
            id="pricing",
        ),
        pytest.param(lambda model: setattr(model.binding, "model", "other-wire"), None, id="wire_model"),
        pytest.param(lambda model: delitem(model.model.bindings, Route.DIRECT), None, id="route_binding"),
        pytest.param(
            lambda model: setitem(model.binding.headers, "anthropic-beta", "other-beta"),
            None,
            id="default_headers",
        ),
        pytest.param(
            lambda model: setitem(model.binding.headers, "anthropic-beta", "other-beta"),
            {"anthropic-beta": "fixture-beta"},
            id="configured_headers",
        ),
    ],
)
def test_resolved_models_cannot_change_the_catalog(
    tmp_path: Path, mutate: Callable[[ResolvedModel], None], headers: dict[str, str] | None
):
    data = yaml.safe_load(MINIMAL_CATALOG)
    entry = data["models"]["fixture-model"]
    entry["pricing"] = {"input_usd_per_million": "2"}
    if headers is not None:
        entry["bindings"]["direct"]["headers"] = headers
    resolver = ModelResolver(write_catalog(tmp_path / "catalog.yaml", yaml.safe_dump(data)))
    resolved = resolver.resolve("fixture-model", route=Route.DIRECT)

    with pytest.raises((AttributeError, TypeError, ValueError)):
        mutate(resolved)

    following = resolver.resolve("fixture-model", route=Route.DIRECT)
    assert following.model.context_window == 100_000
    assert following.binding.model == "fixture-model"
    assert following.binding.headers == (headers or {})
    assert following.expected_cost(input_tokens=1_000_000, output_tokens=0) == Decimal("2")


@pytest.mark.parametrize("route", [Route.DIRECT, Route.AI_GATEWAY])
def test_canonical_names_resolve_without_an_alias(route: Route, tmp_path: Path):
    resolver = make_resolver(tmp_path, **{"claude-opus-5-5": make_entry()})

    resolved = resolver.resolve("claude-opus-5-5", route=route)

    assert resolved.canonical == "claude-opus-5-5"
    assert resolved.binding.model == ("claude-opus-5-5" if route is Route.DIRECT else "anthropic/claude-opus-5-5")


@pytest.mark.parametrize("written", ["opus", "OPUS", "Opus"])
def test_alias_resolution_is_case_insensitive(written: str, tmp_path: Path):
    resolver = make_resolver(tmp_path, aliases={"opus": "claude-opus-5-5"}, **{"claude-opus-5-5": make_entry()})

    assert resolver.resolve(written, route=Route.DIRECT).canonical == "claude-opus-5-5"


def test_wire_model_casing_is_preserved(tmp_path: Path):
    resolver = make_resolver(tmp_path, **{"claude-opus-5-5": make_entry(bindings=both_routes("Claude-Opus-5-5"))})

    resolved = resolver.resolve("CLAUDE-OPUS-5-5", route=Route.DIRECT)

    assert resolved.binding.model == "Claude-Opus-5-5"


def test_unknown_model_error_lists_every_valid_name(tmp_path: Path):
    resolver = make_resolver(
        tmp_path,
        aliases={"sonnet": "claude-sonnet-5"},
        **{"claude-opus-5-5": make_entry(), "claude-sonnet-5": make_entry()},
    )

    with pytest.raises(ValueError, match="Unknown model 'gpt'. Valid models: claude-opus-5-5, claude-sonnet-5, sonnet"):
        resolver.resolve("gpt", route=Route.DIRECT)


def test_resolve_rejects_a_model_owned_by_another_provider(tmp_path: Path):
    resolver = make_resolver(tmp_path, **{"claude-opus-5-5": make_entry()})

    with pytest.raises(ValueError, match="Model 'claude-opus-5-5' belongs to provider 'anthropic', not 'openai'"):
        resolver.resolve("claude-opus-5-5", route=Route.DIRECT, provider="openai")


def test_missing_route_binding(tmp_path: Path):
    resolver = make_resolver(
        tmp_path,
        **{
            "claude-opus-5-5": make_entry(
                bindings={Route.DIRECT: BindingConfig(protocol=ANTHROPIC_MESSAGES, model="claude-opus-5-5")}
            )
        },
    )

    with pytest.raises(ValueError, match="has no 'ai-gateway' binding; available routes: direct"):
        resolver.resolve("claude-opus-5-5", route=Route.AI_GATEWAY)


def test_opt_in_variant_window_and_headers(tmp_path: Path):
    resolver = ModelResolver(write_catalog(tmp_path / "custom.yaml", LONG_CONTEXT_CATALOG))

    base = resolver.resolve("fixture-model", route=Route.DIRECT)
    variant = resolver.resolve("fixture-model-1m", route=Route.DIRECT)

    assert base.binding.model == variant.binding.model
    assert base.model.context_window == 200_000
    assert variant.model.context_window == 1_000_000
    assert variant.binding.headers == {"anthropic-beta": "context-1m-2025-08-07"}
    assert not base.binding.headers


def test_custom_catalog_replaces_shipped(tmp_path: Path):
    path = write_catalog(tmp_path / "custom.yaml", MINIMAL_CATALOG)

    resolver = ModelResolver(path)

    assert resolver.resolve("fixture-model", route=Route.DIRECT, provider=ANTHROPIC).canonical == "fixture-model"
    with pytest.raises(ValueError, match="Unknown model 'sonnet'"):
        resolver.resolve("sonnet", route=Route.DIRECT)


def test_catalog_path_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "catalogs").mkdir()
    write_catalog(tmp_path / "catalogs" / "custom.yaml", MINIMAL_CATALOG)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    write_catalog(tmp_path / "home.yaml", MINIMAL_CATALOG)

    for written in ("catalogs/custom.yaml", "~/home.yaml"):
        assert ModelResolver(written).resolve("fixture-model", route=Route.DIRECT)


@pytest.mark.parametrize(
    ("catalog, match"),
    [
        ("models: [", "not valid YAML"),
        (f"{MINIMAL_CATALOG}unknown_option: 1\n", "Extra inputs are not permitted"),
        (
            MINIMAL_CATALOG.replace("model: fixture-model", "model: fixture-model\n        unknown_option: 1"),
            "Extra inputs are not permitted",
        ),
        ("aliases:\n  opus: claude-opus-x\nmodels: {}", "points at unknown model 'claude-opus-x'"),
        (
            "aliases:\n  fixture-model: fixture-model\n" + MINIMAL_CATALOG,
            "conflicts with a canonical model name",
        ),
        (
            MINIMAL_CATALOG.replace("context_window: 100000", "context_window: 20000\n    max_input_tokens: 100000"),
            "declares 100000 max input tokens above its 20000-token context window",
        ),
        (
            "aliases:\n  Pick: fixture-model\n  pick: other-model\n"
            + MINIMAL_CATALOG
            + MINIMAL_CATALOG.removeprefix("models:\n").replace("fixture-model", "other-model"),
            "Aliases must be unique ignoring case",
        ),
        (MINIMAL_CATALOG.replace("context_window: 100000", "context_window: -1"), "greater than 0"),
        (MINIMAL_CATALOG.replace("context_window: 100000", "context_window: true"), "valid integer"),
        (MINIMAL_CATALOG.replace("    context_window: 100000\n", ""), "context_window\n  Field required"),
        (
            MINIMAL_CATALOG.replace("      direct:", "      directx:"),
            "Input should be 'direct' or 'ai-gateway'",
        ),
        (
            MINIMAL_CATALOG.replace("protocol: anthropic-messages", "protocol: openai-responses"),
            "binds protocol 'openai-responses' for provider 'anthropic'",
        ),
        (
            MINIMAL_CATALOG.replace("  fixture-model:", "  Fixture-Model:"),
            "Canonical model names must be lowercase: 'Fixture-Model'",
        ),
        (
            MINIMAL_CATALOG.replace(
                "    bindings:",
                "    pricing:\n      input_usd_per_million: \"-1\"\n    bindings:",
            ),
            "greater than or equal to 0",
        ),
        (
            MINIMAL_CATALOG.replace(
                "    bindings:",
                "    pricing:\n      input_usd_per_million: .nan\n    bindings:",
            ),
            "finite number",
        ),
        (
            MINIMAL_CATALOG.replace(
                "    bindings:",
                "    pricing:\n      input_usd: \"1\"\n    bindings:",
            ),
            "Extra inputs are not permitted",
        ),
    ],
    ids=[
        "malformed_yaml",
        "unknown_field",
        "unknown_binding_field",
        "unknown_alias_target",
        "alias_shadows_canonical",
        "input_above_window",
        "ambiguous_alias",
        "negative_limit",
        "boolean_limit",
        "missing_window",
        "unknown_route",
        "unsupported_protocol",
        "non_lowercase_canonical",
        "negative_rate",
        "non_finite_rate",
        "unknown_pricing_field",
    ],
)
def test_invalid_catalog_error_has_path(tmp_path: Path, catalog: str, match: str):
    path = tmp_path / "custom.yaml"
    path.write_text(catalog, encoding="utf-8")

    with pytest.raises(ValueError, match=escape(str(path))) as error:
        ModelResolver(path)

    assert match in str(error.value)


def test_missing_catalog_file(tmp_path: Path):
    path = tmp_path / "absent.yaml"
    with pytest.raises(ValueError, match=escape(f"Could not read model catalog {path}")):
        ModelResolver(path)


def test_non_utf8_catalog_error_has_path(tmp_path: Path):
    path = tmp_path / "custom.yaml"
    path.write_bytes(b"\xff")

    with pytest.raises(ValueError, match=escape(str(path))):
        ModelResolver(path)
