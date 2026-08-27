"""Separate OpenRouter/Groq JSON-only claim analysis provider with fallback."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
_RECOMMENDATIONS = {"settle", "request_documents", "reject", "route_to_human"}


class ClaimAnalysisError(RuntimeError):
    pass


def analyze_claim_with_fallback(claim_context: dict[str, Any], retrieval: dict[str, Any]) -> dict[str, Any]:
    """Use the dedicated reasoning models; OCR model settings are never consulted."""
    try:
        result = _openrouter_claim_analysis(claim_context, retrieval)
        result["provider"] = "openrouter"
        return result
    except ClaimAnalysisError as primary_error:
        logger.warning("OpenRouter claim analysis failed; trying Groq fallback: %s", primary_error)
        try:
            result = _groq_claim_analysis(claim_context, retrieval)
            result["provider"] = "groq"
            return result
        except ClaimAnalysisError as fallback_error:
            raise ClaimAnalysisError("Claim analysis is temporarily unavailable from both configured providers") from fallback_error


def _openrouter_claim_analysis(claim_context: dict[str, Any], retrieval: dict[str, Any]) -> dict[str, Any]:
    if not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_LLM_MODEL:
        raise ClaimAnalysisError("OpenRouter claim analysis is not configured")
    return _request_analysis(OPENROUTER_CHAT_COMPLETIONS_URL, settings.OPENROUTER_API_KEY, settings.OPENROUTER_LLM_MODEL, claim_context, retrieval)


def _groq_claim_analysis(claim_context: dict[str, Any], retrieval: dict[str, Any]) -> dict[str, Any]:
    if not settings.GROQ_API_KEY or not settings.GROQ_LLM_MODEL:
        raise ClaimAnalysisError("Groq claim analysis is not configured")
    return _request_analysis(GROQ_CHAT_COMPLETIONS_URL, settings.GROQ_API_KEY, settings.GROQ_LLM_MODEL, claim_context, retrieval)


def _request_analysis(url: str, api_key: str, model: str, claim_context: dict[str, Any], retrieval: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _analysis_prompt()},
            {"role": "user", "content": json.dumps({"claim_context": claim_context, "retrieved_handbook_rules": retrieval.get("results", [])}, default=str)},
        ],
    }
    try:
        response = httpx.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=settings.CLAIM_ANALYSIS_TIMEOUT_SECONDS)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise ClaimAnalysisError("Claim analysis provider returned an invalid response") from exc
    return parse_claim_analysis_response(content)


def parse_claim_analysis_response(content: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(content, dict):
        payload = content
    elif isinstance(content, str):
        stripped = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content.strip(), flags=re.IGNORECASE)
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ClaimAnalysisError("Claim analysis provider returned malformed JSON") from exc
    else:
        raise ClaimAnalysisError("Claim analysis provider returned malformed JSON")
    if not isinstance(payload, dict) or payload.get("recommendation") not in _RECOMMENDATIONS:
        raise ClaimAnalysisError("Claim analysis response has an invalid recommendation")
    confidence = payload.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ClaimAnalysisError("Claim analysis response has an invalid confidence")
    return {
        "recommendation": payload["recommendation"],
        "confidence": float(confidence),
        "summary": str(payload.get("summary") or ""),
        "decision_findings": payload.get("decision_findings") if isinstance(payload.get("decision_findings"), list) else [],
        "reasoning": payload.get("reasoning") if isinstance(payload.get("reasoning"), list) else [],
        "missing_information": payload.get("missing_information") if isinstance(payload.get("missing_information"), list) else [],
        "validation_issues": payload.get("validation_issues") if isinstance(payload.get("validation_issues"), list) else [],
        "consistency_issues": payload.get("consistency_issues") if isinstance(payload.get("consistency_issues"), list) else [],
        "recommended_next_actions": payload.get("recommended_next_actions") if isinstance(payload.get("recommended_next_actions"), list) else [],
    }


def _analysis_prompt() -> str:
    return """You are an insurance claim analysis system. Return ONLY one valid JSON object, with no markdown or explanation outside JSON. Use only the supplied claim data and retrieved handbook rules. The handbook snippets are the sole authority for policy rules: never invent a rule or assume a fact absent from the supplied data. The recommendation is advisory and may ONLY be settle, request_documents, reject, or route_to_human. Rule categories are binding: DOCUMENT_REQUIREMENT supports only requesting documents; POLICY_VALIDATION supports policy/date checks; COVERAGE or EXCLUSION may support coverage conclusions only when their applies_to_products matches the claim product or is ALL; LIMIT, RISK, FRAUD, and HUMAN_REVIEW support routing; SETTLEMENT may support settlement only alongside applicable COVERAGE evidence. Never use a document rule as grounds to reject. If evidence is insufficient or applicability is unclear, use route_to_human; missing evidence should use request_documents. Do not reveal chain-of-thought. decision_findings must give specific category, pass/fail/uncertain outcome, a concrete reason, evidence, and rule_identifier where relevant; never use vague wording without the cause. Cite only supplied handbook chunks using chunk_id and available metadata. Use this schema: {\"recommendation\":\"settle|request_documents|reject|route_to_human\",\"confidence\":0.0,\"decision_findings\":[{\"category\":\"coverage|exclusion|policy|document|conflict|risk|duplicate|other\",\"outcome\":\"pass|fail|uncertain\",\"reason\":\"\",\"rule_identifier\":null,\"evidence\":\"\"}],\"summary\":\"\",\"reasoning\":[],\"missing_information\":[],\"validation_issues\":[],\"consistency_issues\":[],\"recommended_next_actions\":[]}"""
