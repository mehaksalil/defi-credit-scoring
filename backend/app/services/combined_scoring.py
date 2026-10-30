"""Experimental transparent blend of wallet and lending behavior scores.

This is a prototype policy, not a calibrated credit or default-probability model.
"""
from __future__ import annotations

import math
from typing import Any

BEHAVIORAL_WEIGHT = 0.30
LENDING_WEIGHT = 0.70

def risk_level(score: float) -> str:
    if score < 40:
        return "High"
    if score < 70:
        return "Medium"
    return "Low"

def _score_value(value: Any, name: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number from 0 to 100") from exc
    if not math.isfinite(score) or score < 0 or score > 100:
        raise ValueError(f"{name} must be a finite number from 0 to 100")
    return score

def combine_credit_scores(behavioral_score: float, lending_behavior_score: float | None) -> dict[str, Any]:
    """Blend scores when lending evidence exists; otherwise fall back to baseline.

    Lending index already shrinks toward neutral when few borrowing events exist.
    A further 70% maximum composite weight keeps low-evidence lending history
    from overriding the existing behavioral component.
    """
    behavioral = _score_value(behavioral_score, "behavioral_score")
    if lending_behavior_score is None:
        combined = round(behavioral, 2)
        score_type = "behavioral_only_no_lending_history"
        weights = {"behavioral": 1.0, "lending": 0.0}
        formula = "combined=behavioral_score (no lending score available)"
    else:
        lending = _score_value(lending_behavior_score, "lending_behavior_score")
        combined = round(BEHAVIORAL_WEIGHT * behavioral + LENDING_WEIGHT * lending, 2)
        score_type = "experimental_weighted_composite"
        weights = {"behavioral": BEHAVIORAL_WEIGHT, "lending": LENDING_WEIGHT}
        formula = "combined=0.30*behavioral_score+0.70*lending_behavior_score"
    combined = max(0.0, min(100.0, combined))
    return {
        "combined_credit_score": combined,
        "combined_risk_level": risk_level(combined),
        "score_type": score_type,
        "weights": weights,
        "formula": formula,
    }
