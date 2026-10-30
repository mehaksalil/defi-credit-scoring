"""Transparent experimental scoring policy for verified lending features.

This index is deliberately separate from the project's trained Isolation Forest
score. It is suitable for prototyping and explanation, not for real credit decisions.
"""
from __future__ import annotations

import math
from typing import Any

NEUTRAL_SCORE = 50.0
REPAYMENT_WEIGHT = 0.70
DEBT_POSITION_WEIGHT = 0.30
FULL_EVIDENCE_BORROW_EVENTS = 5


def _finite_nonnegative(features: dict[str, Any], name: str) -> float:
    try:
        value = float(features.get(name, 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid lending feature: {name}; expected a finite non-negative number") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid lending feature: {name}; expected a finite non-negative number")
    return value


def compute_lending_behavior_score(features: dict[str, Any]) -> dict[str, Any]:
    """Compute an explainable 0-100 lending-behavior index from Task 2 features.

    Policy:
    - 70% repayment coverage: min(total_repaid / total_borrowed, 1).
    - 30% current debt position: 1 - min(current_debt / current_collateral, 1).
      If debt and collateral are both zero, the debt-position component is 1; if
      debt exists without collateral, it is 0.
    - Evidence adjustment: shrink raw score toward a neutral 50 by
      min(borrow_event_count / 5, 1). This reduces overconfidence after only one
      or two borrow events. The event count is only a rough proxy for evidence,
      not a count of independent, fully settled loans.
    - No borrow history means no score (None), rather than treating missing
      evidence as good or bad behavior.
    """
    if not isinstance(features, dict):
        raise ValueError("Lending features must be a JSON object")

    borrow_count_raw = _finite_nonnegative(features, "borrow_event_count")
    if not borrow_count_raw.is_integer():
        raise ValueError("Invalid lending feature: borrow_event_count; expected an integer")
    borrow_count = int(borrow_count_raw)
    total_borrowed = _finite_nonnegative(features, "total_borrowed")
    total_repaid = _finite_nonnegative(features, "total_repaid")
    current_collateral = _finite_nonnegative(features, "current_collateral")
    current_debt = _finite_nonnegative(features, "current_debt")

    if borrow_count == 0 or total_borrowed == 0:
        return {
            "lending_behavior_score": None,
            "raw_component_score": None,
            "status": "insufficient_history",
            "evidence_level": "none",
            "evidence_factor": 0.0,
            "borrow_event_count": borrow_count,
            "components": {
                "repayment_coverage_ratio": None,
                "debt_position_ratio": None,
                "repayment_weight": REPAYMENT_WEIGHT,
                "debt_position_weight": DEBT_POSITION_WEIGHT,
            },
            "explanation": "No recorded borrowing history is available; no lending-behavior score is assigned.",
        }

    repayment_coverage = min(total_repaid / total_borrowed, 1.0)
    if current_collateral > 0:
        debt_to_collateral = current_debt / current_collateral
        debt_position = 1.0 - min(debt_to_collateral, 1.0)
    else:
        debt_to_collateral = None
        debt_position = 0.0 if current_debt > 0 else 1.0

    raw_score = 100.0 * (
        REPAYMENT_WEIGHT * repayment_coverage
        + DEBT_POSITION_WEIGHT * debt_position
    )
    evidence_factor = min(borrow_count / FULL_EVIDENCE_BORROW_EVENTS, 1.0)
    adjusted_score = NEUTRAL_SCORE + evidence_factor * (raw_score - NEUTRAL_SCORE)
    adjusted_score = round(max(0.0, min(100.0, adjusted_score)), 2)
    raw_score = round(max(0.0, min(100.0, raw_score)), 2)

    if borrow_count < 3:
        evidence_level = "low"
    elif borrow_count < FULL_EVIDENCE_BORROW_EVENTS:
        evidence_level = "limited"
    else:
        evidence_level = "more_observations_not_validated"

    return {
        "lending_behavior_score": adjusted_score,
        "raw_component_score": raw_score,
        "status": "experimental_score_available",
        "evidence_level": evidence_level,
        "evidence_factor": round(evidence_factor, 4),
        "borrow_event_count": borrow_count,
        "components": {
            "repayment_coverage_ratio": round(repayment_coverage, 4),
            "debt_to_collateral_ratio": round(debt_to_collateral, 4) if debt_to_collateral is not None else None,
            "debt_position_ratio": round(debt_position, 4),
            "repayment_weight": REPAYMENT_WEIGHT,
            "debt_position_weight": DEBT_POSITION_WEIGHT,
        },
        "formula": "raw=100*(0.70*repayment_coverage+0.30*debt_position); final=50+evidence_factor*(raw-50)",
        "explanation": (
            "The index weights capped cumulative repayment coverage at 70% and current debt position at 30%, "
            "then shrinks the raw score toward neutral 50 when few borrow events are recorded."
        ),
    }
