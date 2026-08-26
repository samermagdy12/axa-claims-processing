"""Deterministic final claim decisions, deliberately independent of the LLM."""
from __future__ import annotations

from decimal import Decimal
from typing import Any


ALLOWED_DECISIONS = frozenset({"settle", "request_documents", "reject", "route_to_human"})
AUTO_SETTLEMENT_LIMIT_EGP = Decimal("10000")


def decide_claim(*, claim: dict[str, Any], policy: dict[str, Any], processing: dict[str, Any], analysis: dict[str, Any], duplicate_detection: dict[str, Any] | None = None, risk_signals: list[Any] | None = None) -> dict[str, Any]:
    """Apply documented rule priority and preserve every rule that was triggered.

    Priority is request_documents, reject (only evidence-backed),
    route_to_human, then settle.  The first matching outcome is final, while
    the full list remains available to assessors and audit storage.
    """
    rules: list[dict[str, str]] = []
    missing = processing.get("missing_documents") or []
    invalid = processing.get("invalid_documents") or []
    if missing:
        rules.append(_rule("MISSING_REQUIRED_DOCUMENTS", "request_documents", f"Missing required documents: {', '.join(map(str, missing))}."))
    if invalid:
        rules.append(_rule("INVALID_DOCUMENTS", "request_documents", "One or more uploaded documents do not match the required document type."))

    if _supported_exclusion(analysis):
        rules.append(_rule("COVERAGE_EXCLUSION_SUPPORTED", "reject", "The claim is clearly excluded or not covered by the retrieved policy terms."))

    amount = _decimal(claim.get("claimed_amount"))
    if amount is not None and amount > AUTO_SETTLEMENT_LIMIT_EGP:
        rules.append(_rule("AMOUNT_OVER_AUTO_SETTLEMENT_LIMIT", "route_to_human", "Claim amount exceeds the EGP 10,000 automatic settlement limit."))
    if processing.get("consistency", {}).get("has_conflicts"):
        rules.append(_rule("CONSISTENCY_CONFLICT", "route_to_human", "Conflicting information was found across claim documents."))
    if _duplicate_detected(processing, duplicate_detection):
        rules.append(_rule("DUPLICATE_DETECTED", "route_to_human", "A possible duplicate claim or document requires specialist review."))
    if risk_signals:
        rules.append(_rule("RISK_SIGNAL", "route_to_human", "This claim requires specialist review."))
    if processing.get("manual_review_required"):
        rules.append(_rule("MANUAL_REVIEW_REQUIRED", "route_to_human", "The available document information requires specialist review."))
    if policy and str(policy.get("status") or "").upper() != "ACTIVE":
        rules.append(_rule("POLICY_VALIDATION_FAILED", "route_to_human", "Policy eligibility requires specialist review."))
    if analysis.get("recommendation") == "route_to_human":
        rules.append(_rule("LLM_RECOMMENDS_HUMAN_REVIEW", "route_to_human", "The evidence-based analysis recommends specialist review."))

    if _eligible_to_settle(claim, policy, processing, analysis, amount):
        rules.append(_rule("AUTO_SETTLEMENT_ELIGIBLE", "settle", "All automatic-settlement conditions passed."))

    final = next((rule for outcome in ("request_documents", "reject", "route_to_human", "settle") for rule in rules if rule["outcome"] == outcome), _rule("INSUFFICIENT_EVIDENCE", "route_to_human", "The claim cannot be safely decided automatically."))
    decision = final["outcome"]
    return {
        "llm_recommendation": analysis.get("recommendation") if analysis.get("recommendation") in ALLOWED_DECISIONS else "route_to_human",
        "final_decision": decision,
        "decision_source": "business_rules",
        "auto_processed": decision == "settle",
        "human_review_required": decision == "route_to_human",
        "triggered_rules": rules or [final],
        "reason": final["reason"],
        "missing_documents": missing,
        "customer_message": _customer_message(decision),
        "handbook_references": analysis.get("retrieved_handbook_references") or [],
    }


def _eligible_to_settle(claim: dict[str, Any], policy: dict[str, Any], processing: dict[str, Any], analysis: dict[str, Any], amount: Decimal | None) -> bool:
    return bool(
        not processing.get("missing_documents")
        and not processing.get("invalid_documents")
        and not processing.get("manual_review_required")
        and not processing.get("consistency", {}).get("has_conflicts")
        and not processing.get("duplicate_documents")
        and str(policy.get("status") or "").upper() == "ACTIVE"
        and amount is not None and amount <= AUTO_SETTLEMENT_LIMIT_EGP
        and analysis.get("recommendation") == "settle"
        and bool(analysis.get("retrieved_handbook_references"))
    )


def _supported_exclusion(analysis: dict[str, Any]) -> bool:
    if analysis.get("recommendation") != "reject" or not analysis.get("retrieved_handbook_references"):
        return False
    evidence = " ".join(str(item.get(key, "")) for item in analysis.get("reasoning") or [] if isinstance(item, dict) for key in ("finding", "evidence"))
    evidence = f"{analysis.get('summary', '')} {evidence}".casefold()
    return "exclude" in evidence or "not covered" in evidence or "not cover" in evidence


def _duplicate_detected(processing: dict[str, Any], duplicate_detection: dict[str, Any] | None) -> bool:
    return bool(processing.get("duplicate_documents") or (duplicate_detection or {}).get("duplicate_detected") or (duplicate_detection or {}).get("has_duplicates"))


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _rule(rule_id: str, outcome: str, reason: str) -> dict[str, str]:
    return {"rule_id": rule_id, "outcome": outcome, "reason": reason}


def _customer_message(decision: str) -> str:
    return {
        "settle": "Your claim has been approved and will proceed to settlement.",
        "request_documents": "We need additional documents or information before we can continue processing your claim.",
        "reject": "We are unable to approve this claim because it is not covered under the applicable policy terms.",
        "route_to_human": "Your claim is being reviewed by a claims specialist.",
    }[decision]
