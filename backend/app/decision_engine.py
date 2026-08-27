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
        rules.append(_rule("MISSING_REQUIRED_DOCUMENT", "request_documents", f"Processing is on hold because the required {', '.join(map(str, missing))} has not been uploaded."))
    if invalid:
        names = ", ".join(str(item.get("document_type") or item.get("document_id") or "document") for item in invalid if isinstance(item, dict))
        rules.append(_rule("INVALID_DOCUMENT", "request_documents", f"Processing is on hold because the uploaded {names or 'document'} could not be validated as the required document type."))

    if not _policy_is_valid(policy):
        rules.append(_rule("POLICY_VALIDATION_FAILED", "reject", _policy_failure_reason(claim, policy)))
    elif _supported_exclusion(analysis, policy):
        rules.append(_rule("POLICY_EXCLUSION_APPLIES", "reject", _exclusion_reason(analysis)))

    amount = _decimal(claim.get("claimed_amount"))
    if amount is not None and amount > AUTO_SETTLEMENT_LIMIT_EGP:
        rules.append(_rule("CLAIM_AMOUNT_ABOVE_AUTO_APPROVAL_LIMIT", "route_to_human", f"Human review is required because the claimed amount of EGP {_money(amount)} exceeds the automatic approval limit of EGP 10,000."))
    if processing.get("consistency", {}).get("has_conflicts"):
        rules.append(_rule("DOCUMENT_CONFLICT", "route_to_human", _conflict_reason(processing)))
    if _duplicate_detected(processing, duplicate_detection):
        rules.append(_rule("POSSIBLE_DUPLICATE_CLAIM", "route_to_human", "Human review is required because another claim with the same policy, claim type, incident date, and claimed amount was detected."))
    if risk_signals:
        rules.append(_rule("RISK_SIGNAL_DETECTED", "route_to_human", "Human review is required because a deterministic risk indicator was detected."))
    if processing.get("manual_review_required"):
        rules.append(_rule("MANUAL_REVIEW_REQUIRED", "route_to_human", "Human review is required because document validation found information that could not be resolved automatically."))
    if amount is not None and _decimal(policy.get("remaining_limit")) is not None and _decimal(policy.get("remaining_limit")) < amount:
        rules.append(_rule("INSUFFICIENT_REMAINING_LIMIT", "route_to_human", f"Human review is required because the remaining policy limit of EGP {_money(_decimal(policy.get('remaining_limit')))} is lower than the claimed amount of EGP {_money(amount)}."))
    if analysis.get("recommendation") == "route_to_human":
        rules.append(_rule("POLICY_COVERAGE_UNCERTAIN", "route_to_human", _uncertainty_reason(analysis)))

    if _eligible_to_settle(claim, policy, processing, analysis, amount):
        rules.append(_rule("AUTO_APPROVED", "settle", "The claim was automatically approved because all required documents were validated, the policy was active on the incident date, the claimed amount was within the automatic approval limit, sufficient policy limit remained, no duplicate or conflict was detected, and retrieved policy evidence supports coverage."))

    final = next((rule for outcome in ("request_documents", "reject", "route_to_human", "settle") for rule in rules if rule["outcome"] == outcome), _rule("INSUFFICIENT_HANDBOOK_EVIDENCE", "route_to_human", "Human review is required because the available policy evidence does not provide sufficient support for an automatic coverage decision."))
    decision = final["outcome"]
    return {
        "llm_recommendation": analysis.get("recommendation") if analysis.get("recommendation") in ALLOWED_DECISIONS else "route_to_human",
        "final_decision": decision,
        "decision_source": "business_rules",
        "auto_processed": decision == "settle",
        "human_review_required": decision == "route_to_human",
        "triggered_rules": rules or [final],
        "reason": final["reason"],
        "reason_code": final["rule_id"],
        "decision_trace": _decision_trace(claim, policy, processing, analysis, duplicate_detection, rules, final),
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
        and _policy_is_valid(policy)
        and amount is not None and amount <= AUTO_SETTLEMENT_LIMIT_EGP
        and _decimal(policy.get("remaining_limit")) is not None and _decimal(policy.get("remaining_limit")) >= amount
        and analysis.get("recommendation") == "settle"
        and _supported_settlement(analysis, policy)
    )


def _policy_is_valid(policy: dict[str, Any]) -> bool:
    return bool(policy and str(policy.get("status") or "").upper() == "ACTIVE" and policy.get("validation_passed", True))


def _supported_exclusion(analysis: dict[str, Any], policy: dict[str, Any]) -> bool:
    """Reject only for a cited, applicable coverage/exclusion rule.

    Retrieval is intentionally broad, so merely returning an exclusions or
    documents chunk is not evidence that it applies to this claim.
    """
    if analysis.get("recommendation") != "reject":
        return False
    evidence = _cited_evidence(analysis, policy)
    return any(
        reference.get("rule_category") in {"EXCLUSION", "COVERAGE"}
        and any(term in finding.casefold() for term in ("exclude", "not covered", "no cover", "not cover"))
        for reference, finding in evidence
    )


def _supported_settlement(analysis: dict[str, Any], policy: dict[str, Any]) -> bool:
    """A settlement needs cited, applicable coverage and settlement authority."""
    categories = {reference.get("rule_category") for reference, _ in _cited_evidence(analysis, policy)}
    return {"COVERAGE", "SETTLEMENT"}.issubset(categories)


def _cited_evidence(analysis: dict[str, Any], policy: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    references = {
        str(reference.get("chunk_id")): reference
        for reference in analysis.get("retrieved_handbook_references") or []
        if isinstance(reference, dict) and _reference_applies(reference, policy)
    }
    evidence: list[tuple[dict[str, Any], str]] = []
    for finding in analysis.get("reasoning") or []:
        if not isinstance(finding, dict):
            continue
        text = " ".join(str(finding.get(key, "")) for key in ("finding", "evidence"))
        for citation in finding.get("handbook_references") or []:
            if not isinstance(citation, dict):
                continue
            reference = references.get(str(citation.get("chunk_id")))
            if reference:
                evidence.append((reference, text))
    return evidence


def _reference_applies(reference: dict[str, Any], policy: dict[str, Any]) -> bool:
    products = reference.get("applies_to_products", "ALL")
    if isinstance(products, str):
        values = {item.strip().upper() for item in products.split(",") if item.strip()}
    elif isinstance(products, list):
        values = {str(item).strip().upper() for item in products if str(item).strip()}
    else:
        return False
    product = str(policy.get("product_line") or "").strip().upper()
    return bool(values) and ("ALL" in values or product in values)


def _duplicate_detected(processing: dict[str, Any], duplicate_detection: dict[str, Any] | None) -> bool:
    return bool(processing.get("duplicate_documents") or (duplicate_detection or {}).get("duplicate_detected") or (duplicate_detection or {}).get("has_duplicates"))


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _policy_failure_reason(claim: dict[str, Any], policy: dict[str, Any]) -> str:
    incident, end = claim.get("incident_date"), policy.get("end_date")
    if incident and end:
        return f"The claim was rejected because the incident date {incident} falls outside the active policy period, which ended on {end}."
    return "The claim was rejected because the policy is not active for the incident date."


def _exclusion_reason(analysis: dict[str, Any]) -> str:
    for finding in analysis.get("decision_findings") or analysis.get("reasoning") or []:
        if isinstance(finding, dict) and str(finding.get("reason") or finding.get("finding") or "").strip():
            return f"The claim was rejected because {str(finding.get('reason') or finding.get('finding')).strip()}"
    return "The claim was rejected because an applicable retrieved policy clause explicitly excludes the reported loss from coverage."


def _conflict_reason(processing: dict[str, Any]) -> str:
    conflict = (processing.get("consistency", {}).get("conflicts") or [{}])[0]
    field = str(conflict.get("field") or "information")
    return f"Human review is required because conflicting {field.replace('_', ' ')} information was extracted from the uploaded documents."


def _uncertainty_reason(analysis: dict[str, Any]) -> str:
    for finding in analysis.get("decision_findings") or []:
        if isinstance(finding, dict) and finding.get("outcome") == "uncertain" and finding.get("reason"):
            return str(finding["reason"])
    return "Human review is required because the available policy evidence does not provide sufficient support for an automatic coverage decision."


def _money(value: Decimal | None) -> str:
    return f"{value:,.2f}" if value is not None else "unknown"


def _decision_trace(claim, policy, processing, analysis, duplicate_detection, rules, final):
    """Persist a readable ordered audit trail, including rules that passed."""
    triggered = {rule["rule_id"] for rule in rules}
    amount = _decimal(claim.get("claimed_amount")); remaining = _decimal(policy.get("remaining_limit"))
    items = [
        ("required_documents", "MISSING_REQUIRED_DOCUMENT" not in triggered, "All required documents were uploaded." if not processing.get("missing_documents") else f"Missing: {', '.join(map(str, processing['missing_documents']))}."),
        ("document_validation", "INVALID_DOCUMENT" not in triggered and not processing.get("manual_review_required"), "Uploaded documents were validated." if not processing.get("invalid_documents") else "One or more uploaded documents were invalid."),
        ("policy_status", "POLICY_VALIDATION_FAILED" not in triggered, "The policy is active and covers the incident date." if _policy_is_valid(policy) else _policy_failure_reason(claim, policy)),
        ("claim_amount", "CLAIM_AMOUNT_ABOVE_AUTO_APPROVAL_LIMIT" not in triggered, "The claimed amount is within the automatic approval limit." if amount is not None and amount <= AUTO_SETTLEMENT_LIMIT_EGP else f"Claimed amount is EGP {_money(amount)}; automatic limit is EGP 10,000."),
        ("remaining_limit", "INSUFFICIENT_REMAINING_LIMIT" not in triggered, "The remaining policy limit is sufficient." if remaining is not None and amount is not None and remaining >= amount else "The remaining policy limit is insufficient or unavailable."),
        ("duplicate_check", "POSSIBLE_DUPLICATE_CLAIM" not in triggered, "No duplicate claim was found." if not _duplicate_detected(processing, duplicate_detection) else "A possible duplicate claim was found."),
        ("coverage_evidence", _supported_settlement(analysis, policy) or _supported_exclusion(analysis, policy), "Applicable handbook evidence was cited." if (_supported_settlement(analysis, policy) or _supported_exclusion(analysis, policy)) else f"No applicable coverage and settlement evidence was accepted for {policy.get('product_line', 'this')} / {claim.get('claim_type', 'claim')}.")]
    trace = [{"rule": rule, "result": "passed" if passed else "failed", "details": details} for rule, passed, details in items]
    trace.append({"rule": "final_decision", "result": "passed", "details": f"{final['outcome']}: {final['reason']}"})
    return trace


def _rule(rule_id: str, outcome: str, reason: str) -> dict[str, str]:
    return {"rule_id": rule_id, "outcome": outcome, "reason": reason}


def _customer_message(decision: str) -> str:
    return {
        "settle": "Your claim has been approved and will proceed to settlement.",
        "request_documents": "We need additional documents or information before we can continue processing your claim.",
        "reject": "We are unable to approve this claim because it is not covered under the applicable policy terms.",
        "route_to_human": "Your claim is being reviewed by a claims specialist.",
    }[decision]
