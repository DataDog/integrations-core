# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Extract key components from Datadog monitor queries for template matching.
Uses regex to identify metric(s) and formula structure (anomaly, rate, direct, etc.).
Used for recommended monitor threshold analysis and query validation.
See: https://datadoghq.atlassian.net/browse/MOPU-288
"""
import json
import os
import re
from typing import Optional

# Formula types
ANOMALY = "anomaly"
RATE = "rate"
RATE_INVERSE = "rate_inverse"
DIRECT = "direct"
HANG_RATE = "hang_rate"  # custom: hang.duration / session.time_spent

# Regex patterns (order matters for extraction)
# anomalies(avg:METRIC{ or anomalies(sum:METRIC{
ANOMALY_METRIC = re.compile(
    r"anomalies\s*\(\s*(?:avg|sum)\s*:\s*([\w.]+)\s*\{"
)
# Rate: (sum:METRIC_A{...}.as_count() / sum:METRIC_B{...}.as_count())
RATE_PATTERN = re.compile(
    r"\(\s*sum\s*:\s*([\w.]+)\s*\{[^}]*\}\s*\.\s*as_count\s*\(\s*\)\s*/\s*sum\s*:\s*([\w.]+)\s*\{"
)
# Rate inverse: (1 - (sum:error_free{...} / sum:inactive{...}))
RATE_INVERSE_PATTERN = re.compile(
    r"\(\s*1\s*-\s*\(\s*sum\s*:\s*([\w.]+)\s*\{[^}]*\}[^/]*/\s*[^)]*sum\s*:\s*([\w.]+)\s*\{"
)
# Direct: percentile(last_1h):p75:METRIC{ or avg(last_5m):avg:METRIC{
# Capture outer aggregator (percentile|avg|sum), inner (p75|p50|p90|avg|sum), metric
DIRECT_METRIC = re.compile(
    r"(percentile|avg|sum)\s*\(\s*[^)]+\)\s*:\s*(p75|p50|p90|avg|sum)\s*:\s*([\w.]+)\s*\{"
)
# Hang rate: hang.duration / session.time_spent (with cutoff_min on numerator only)
HANG_RATE_PATTERN = re.compile(
    r"rum\.measure\.error\.hang\.duration.*?/\s*sum\s*:\s*rum\.measure\.session\.time_spent"
)
# Exclude: denominator wrapped in cutoff_min (template has raw sum, not cutoff_min)
DENOM_CUTOFF_MIN = re.compile(r"/\s*cutoff_min\s*\(")
# Exclude: direct metric with multiplier/divisor (e.g. metric * 10 > X) - threshold in different units
FORMULA_MULTIPLIER = re.compile(r"\}\s*[\*\/]\s*[\d.e]+")


def extract_query_components(query: str) -> Optional[dict]:
    """
    Extract metric(s) and formula_type from a Datadog query string.
    Returns dict with: metric, formula_type, secondary_metric (for rate types).
    Returns None if query cannot be parsed.
    """
    if not query or not isinstance(query, str):
        return None
    q = query.strip()

    # Try anomaly first
    m = ANOMALY_METRIC.search(q)
    if m:
        return {
            "metric": m.group(1),
            "formula_type": ANOMALY,
            "secondary_metric": None,
        }

    # Exclude queries where denominator uses cutoff_min (differs from templates)
    if DENOM_CUTOFF_MIN.search(q):
        return None

    # Try rate_inverse (browser_error_rate)
    m = RATE_INVERSE_PATTERN.search(q)
    if m:
        num, denom = m.group(1), m.group(2)
        if "error_free" in num and "inactive" in denom:
            # Template requires avg() and .as_rate(); exclude sum() or .as_count()
            if ".as_count()" in q:
                return None
            if not re.match(r"^\s*avg\s*\(", q):
                return None
            return {
                "metric": num,
                "formula_type": RATE_INVERSE,
                "secondary_metric": denom,
            }

    # Try hang_rate (mobile_hang_rate)
    if HANG_RATE_PATTERN.search(q):
        return {
            "metric": "rum.measure.error.hang.duration",
            "formula_type": HANG_RATE,
            "secondary_metric": "rum.measure.session.time_spent",
        }

    # Try rate (mobile_anr_rate, mobile_crash_free_session_rate)
    m = RATE_PATTERN.search(q)
    if m:
        return {
            "metric": m.group(1),
            "formula_type": RATE,
            "secondary_metric": m.group(2),
        }

    # Try direct (browser_loading_time, mobile_app_startup_time, etc.)
    m = DIRECT_METRIC.search(q)
    if m:
        # Exclude metric * N or metric / N - threshold semantics differ from template
        if FORMULA_MULTIPLIER.search(q):
            return None
        return {
            "metric": m.group(3),
            "formula_type": DIRECT,
            "secondary_metric": None,
            "aggregator": m.group(1),
            "inner_aggregator": m.group(2),
        }

    return None


def components_match(user_components: dict, template_sig: dict) -> bool:
    """
    Check if user query components match template signature.
    Requires: same metric, same formula_type, same secondary_metric (when applicable).
    For direct: same aggregator and inner_aggregator (percentile vs avg matters).
    """
    if not user_components or not template_sig:
        return False
    if user_components.get("formula_type") != template_sig.get("formula_type"):
        return False
    if user_components.get("metric") != template_sig.get("metric"):
        return False
    # For rate types, secondary_metric must match
    t_sec = template_sig.get("secondary_metric")
    u_sec = user_components.get("secondary_metric")
    if t_sec is not None:
        if u_sec is None:
            return False
        if t_sec != u_sec:
            return False
    # For direct: aggregator and inner_aggregator must match (percentile vs avg)
    if user_components.get("formula_type") == DIRECT:
        if user_components.get("aggregator") != template_sig.get("aggregator"):
            return False
        if user_components.get("inner_aggregator") != template_sig.get("inner_aggregator"):
            return False
    return True


def match_template_by_query(user_query: str, template_signatures: dict) -> Optional[str]:
    """
    Return template_id if user_query matches a template's signature.
    """
    user_components = extract_query_components(user_query)
    if not user_components:
        return None
    for template_id, template_sig in template_signatures.items():
        if components_match(user_components, template_sig):
            return template_id
    return None


def load_template_signatures(templates_dir: str) -> dict:
    """
    Load template query signatures from all JSON files in templates_dir.
    templates_dir can point to monitor assets (e.g. integrations-internal-core/real_user_monitoring/assets/monitors).
    Returns {template_id: {metric, formula_type, secondary_metric?}}.
    """
    signatures = {}
    if not os.path.isdir(templates_dir):
        return signatures
    for filename in os.listdir(templates_dir):
        if not filename.endswith(".json"):
            continue
        template_id = filename.replace(".json", "")
        filepath = os.path.join(templates_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
            query = data.get("definition", {}).get("query")
            if not query:
                continue
            components = extract_query_components(query)
            if components:
                signatures[template_id] = components
        except Exception:
            pass
    return signatures
