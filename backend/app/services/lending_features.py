"""Feature engineering for verified LendingPool activity.

These features are derived from confirmed contract events plus the contract's
current collateral/debt state. This module intentionally does not assign a
credit score; score policy is defined separately so features can be tested and
reviewed before being used in scoring.
"""
from __future__ import annotations

from typing import Any


LENDING_FEATURE_NAMES = [
    "deposit_event_count",
    "withdrawal_event_count",
    "borrow_event_count",
    "repayment_event_count",
    "lending_event_count",
    "total_deposited",
    "total_withdrawn",
    "net_deposited",
    "total_borrowed",
    "total_repaid",
    "current_collateral",
    "current_debt",
    "repayment_coverage_ratio",
    "remaining_debt_ratio",
    "withdrawal_to_deposit_ratio",
    "debt_to_collateral_ratio",
    "has_borrow_history",
    "has_repayment_history",
    "has_open_debt",
]


def _number(value: Any, field: str) -> float:
    """Convert a response value to a finite non-negative float."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid lending-history field: {field}") from exc
    if number < 0 or number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"Invalid lending-history field: {field}; expected finite non-negative number")
    return number


def _count(counts: dict[str, Any], name: str) -> int:
    value = _number(counts.get(name, 0), f"counts.{name}")
    if not value.is_integer():
        raise ValueError(f"Invalid lending-history field: counts.{name}; expected integer")
    return int(value)


def compute_lending_features(history: dict[str, Any]) -> dict[str, int | float]:
    """Build an ordered, model-ready feature vector from lending-history JSON.

    Ratio semantics:
    - repayment_coverage_ratio = cumulative repaid / cumulative borrowed, capped at 1.
      It is 0 when the wallet has never borrowed; `has_borrow_history` distinguishes
      no loan history from an unrepaid loan.
    - remaining_debt_ratio = current debt / cumulative borrowed, capped at 1.
    - withdrawal_to_deposit_ratio = cumulative withdrawals / cumulative deposits,
      capped at 1; 0 if no deposits have been recorded.
    - debt_to_collateral_ratio = current debt / current collateral; 0 when collateral
      is zero. `has_open_debt` helps distinguish no debt from no collateral.

    These are behavioral descriptors, not proven default-risk probabilities.
    """
    if not isinstance(history, dict):
        raise ValueError("Lending history must be a JSON object")
    counts = history.get("counts") or {}
    totals = history.get("totals") or {}
    state = history.get("current_state") or {}
    if not all(isinstance(part, dict) for part in (counts, totals, state)):
        raise ValueError("Lending history counts, totals, and current_state must be objects")

    deposit_count = _count(counts, "deposit")
    withdrawal_count = _count(counts, "withdraw")
    borrow_count = _count(counts, "borrow")
    repayment_count = _count(counts, "repay")
    event_count = deposit_count + withdrawal_count + borrow_count + repayment_count

    total_deposited = _number(totals.get("deposited", 0), "totals.deposited")
    total_withdrawn = _number(totals.get("withdrawn", 0), "totals.withdrawn")
    total_borrowed = _number(totals.get("borrowed", 0), "totals.borrowed")
    total_repaid = _number(totals.get("repaid", 0), "totals.repaid")
    current_collateral = _number(state.get("collateral", 0), "current_state.collateral")
    current_debt = _number(state.get("debt", 0), "current_state.debt")

    repayment_coverage_ratio = min(1.0, total_repaid / total_borrowed) if total_borrowed > 0 else 0.0
    remaining_debt_ratio = min(1.0, current_debt / total_borrowed) if total_borrowed > 0 else 0.0
    withdrawal_to_deposit_ratio = min(1.0, total_withdrawn / total_deposited) if total_deposited > 0 else 0.0
    debt_to_collateral_ratio = current_debt / current_collateral if current_collateral > 0 else 0.0

    features: dict[str, int | float] = {
        "deposit_event_count": deposit_count,
        "withdrawal_event_count": withdrawal_count,
        "borrow_event_count": borrow_count,
        "repayment_event_count": repayment_count,
        "lending_event_count": event_count,
        "total_deposited": round(total_deposited, 8),
        "total_withdrawn": round(total_withdrawn, 8),
        "net_deposited": round(total_deposited - total_withdrawn, 8),
        "total_borrowed": round(total_borrowed, 8),
        "total_repaid": round(total_repaid, 8),
        "current_collateral": round(current_collateral, 8),
        "current_debt": round(current_debt, 8),
        "repayment_coverage_ratio": round(repayment_coverage_ratio, 8),
        "remaining_debt_ratio": round(remaining_debt_ratio, 8),
        "withdrawal_to_deposit_ratio": round(withdrawal_to_deposit_ratio, 8),
        "debt_to_collateral_ratio": round(debt_to_collateral_ratio, 8),
        "has_borrow_history": int(borrow_count > 0),
        "has_repayment_history": int(repayment_count > 0),
        "has_open_debt": int(current_debt > 0),
    }
    return features
