"""Portfolio construction and constraint validation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from itertools import product

from .errors import ValidationError


@dataclass(slots=True)
class PortfolioGenerationConstraints:
    asset_caps: dict[str, float] = field(default_factory=dict)
    group_caps: dict[str, float] = field(default_factory=dict)
    groups: dict[str, list[str]] = field(default_factory=dict)
    cash_min: float = 0.0
    btc_cap: float | None = None


@dataclass(slots=True)
class WeightRange:
    min_weight: float
    max_weight: float
    step: float


def validate_fixed_weight_portfolio(weights: dict[str, float], tolerance: float = 1e-6) -> None:
    if not weights:
        raise ValidationError("weights cannot be empty")

    total = 0.0
    for asset_id, weight in weights.items():
        if not asset_id:
            raise ValidationError("asset identifier cannot be empty")
        if weight < 0:
            raise ValidationError(f"weight cannot be negative: {asset_id}")
        total += weight

    if abs(total - 1.0) > tolerance:
        raise ValidationError(f"weight sum invalid: {total}")


def deterministic_portfolio_id(weights: dict[str, float]) -> str:
    normalized = ";".join(f"{k.upper()}:{weights[k]:.8f}" for k in sorted(weights.keys()))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"pf-{digest[:16]}"


def _validate_constraints(weights: dict[str, float], constraints: PortfolioGenerationConstraints) -> bool:
    for asset_id, cap in constraints.asset_caps.items():
        if weights.get(asset_id.upper(), 0.0) > cap:
            return False

    if constraints.btc_cap is not None and weights.get("BTC", 0.0) > constraints.btc_cap:
        return False

    if weights.get("CASH", 0.0) < constraints.cash_min:
        return False

    for group_name, cap in constraints.group_caps.items():
        members = [a.upper() for a in constraints.groups.get(group_name, [])]
        group_weight = sum(weights.get(a, 0.0) for a in members)
        if group_weight > cap:
            return False

    return True


def generate_portfolios(
    ranges: dict[str, WeightRange],
    constraints: PortfolioGenerationConstraints,
    tolerance: float = 1e-6,
) -> list[dict[str, float]]:
    if not ranges:
        raise ValidationError("ranges cannot be empty")

    assets = [asset.upper() for asset in ranges.keys()]
    choices: list[list[float]] = []

    for asset in assets:
        r = ranges[asset]
        if r.step <= 0:
            raise ValidationError(f"step must be positive for {asset}")
        values: list[float] = []
        current = r.min_weight
        while current <= r.max_weight + 1e-12:
            values.append(round(current, 10))
            current += r.step
        choices.append(values)

    candidates: list[dict[str, float]] = []
    for combo in product(*choices):
        weights = {assets[idx]: combo[idx] for idx in range(len(assets))}
        total = sum(weights.values())
        if abs(total - 1.0) > tolerance:
            continue
        if not _validate_constraints(weights, constraints):
            continue
        candidates.append(weights)

    return candidates
