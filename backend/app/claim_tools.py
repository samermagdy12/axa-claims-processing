"""Strict, claim-scoped tools exposed to the claim-analysis model."""
from __future__ import annotations

import json
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import text

from app.claim_processing import build_claim_processing_summary, normalize_document_data
from app.decision_engine import decide_claim
from app.config import settings
from app.handbook_embeddings import OpenRouterEmbedder
from app.handbook_knowledge import ChromaHandbookVectorStore
from app.handbook_retrieval import HandbookRetriever


class _ClaimId(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(min_length=1, max_length=64)


class SearchPolicyDocs(_ClaimId):
    query: str = Field(min_length=2, max_length=1000)
    product_line: str | None = Field(default=None, max_length=30)
    claim_type: str | None = Field(default=None, max_length=80)
    rule_category: str | None = Field(default=None, max_length=40)


class SubmitRecommendation(_ClaimId):
    recommendation: str = Field(pattern=r"^(settle|request_documents|reject|route_to_human)$")
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(default="", max_length=4000)
    decision_findings: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    reasoning: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    missing_information: list[Any] = Field(default_factory=list, max_length=30)
    validation_issues: list[Any] = Field(default_factory=list, max_length=30)
    consistency_issues: list[Any] = Field(default_factory=list, max_length=30)
    recommended_next_actions: list[Any] = Field(default_factory=list, max_length=30)


TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "extract_claim", "description": "Get the authorized structured context for the current claim.", "parameters": _ClaimId.model_json_schema()}},
    {"type": "function", "function": {"name": "lookup_policy", "description": "Get the authorized policy associated with the current claim.", "parameters": _ClaimId.model_json_schema()}},
    {"type": "function", "function": {"name": "search_policy_docs", "description": "Search AXA handbook evidence for the current claim.", "parameters": SearchPolicyDocs.model_json_schema()}},
    {"type": "function", "function": {"name": "validate_claim", "description": "Get deterministic document, policy, duplicate, and limit validation.", "parameters": _ClaimId.model_json_schema()}},
    {"type": "function", "function": {"name": "approve_or_route_claim", "description": "Submit an advisory recommendation; deterministic rules remain final authority.", "parameters": SubmitRecommendation.model_json_schema()}},
]


class ClaimToolExecutor:
    """Only exposes the authorized claim; no tool can select arbitrary records."""
    def __init__(self, claim_id: str, current_user: dict, db, provider: str = "unknown"):
        self.claim_id, self.current_user, self.db, self.provider = str(claim_id), current_user, db, provider
        self.retrieved: dict[str, dict[str, Any]] = {}
        self.submission: dict[str, Any] | None = None

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        started = time.monotonic()
        try:
            model = {"extract_claim": _ClaimId, "lookup_policy": _ClaimId, "validate_claim": _ClaimId,
                     "search_policy_docs": SearchPolicyDocs, "approve_or_route_claim": SubmitRecommendation}.get(name)
            if model is None:
                raise ValueError("Unknown tool")
            parsed = model.model_validate(arguments)
            if parsed.claim_id != self.claim_id:
                raise ValueError("Tool access is limited to the active claim")
            result = getattr(self, f"_{name}")(parsed)
            self._audit(name, arguments, True, started)
            return {"ok": True, "result": result}
        except (ValidationError, ValueError) as exc:
            self._audit(name, arguments, False, started)
            return {"ok": False, "error": str(exc)}
        except Exception:
            self._audit(name, arguments, False, started)
            return {"ok": False, "error": "Tool execution failed safely; route to human review if evidence cannot be obtained."}

    def _claim_policy(self) -> dict[str, Any]:
        row = self.db.execute(text("""SELECT c.claim_id,c.policy_id,c.claim_type,c.incident_date,c.submission_date,c.claimed_amount,c.description,c.status,
            p.user_id,p.policy_number,p.product_line,p.status AS policy_status,p.start_date,p.end_date,p.annual_limit,p.remaining_limit,p.deductible,p.riders
            FROM claims c JOIN policies p ON p.policy_id=c.policy_id WHERE c.claim_id=:claim_id"""), {"claim_id": self.claim_id}).mappings().first()
        if not row:
            raise ValueError("Claim not found")
        if self.current_user["role_name"] == "Customer" and str(row["user_id"]) != str(self.current_user["user_id"]):
            raise ValueError("Unauthorized claim")
        return dict(row)

    def _processing(self) -> dict[str, Any]:
        required = [dict(x) for x in self.db.execute(text("SELECT document_type,is_required,status FROM claim_required_documents WHERE claim_id=:claim_id"), {"claim_id": self.claim_id}).mappings().all()]
        docs = [dict(x) for x in self.db.execute(text("SELECT document_id,document_type FROM claim_documents WHERE claim_id=:claim_id"), {"claim_id": self.claim_id}).mappings().all()]
        extracted = self.db.execute(text("SELECT extracted_data FROM claim_extractions WHERE claim_id=:claim_id ORDER BY extracted_at"), {"claim_id": self.claim_id}).mappings().all()
        by_id = {}
        for row in extracted:
            value = row["extracted_data"]; value = json.loads(value) if isinstance(value, str) else value
            if isinstance(value, dict) and value.get("document_id"): by_id[str(value["document_id"])] = value
        processed = []
        for doc in docs:
            item = by_id.get(str(doc["document_id"]), {})
            validation = item.get("document_validation") or {"validation_passed": None, "reason": "Document has not been extracted yet."}
            processed.append({"document_id": str(doc["document_id"]), "document_type": doc["document_type"], "normalized_data": item.get("normalized_data") or normalize_document_data(doc["document_type"], item.get("structured_data")), "validation": validation})
        return build_claim_processing_summary(required, processed)

    def _extract_claim(self, _: _ClaimId) -> dict[str, Any]:
        row, processing = self._claim_policy(), self._processing()
        return {"claim_id": str(row["claim_id"]), "claim_type": row["claim_type"], "product_line": row["product_line"], "incident_date": row["incident_date"], "submission_date": row["submission_date"], "claimed_amount": row["claimed_amount"], "description": row["description"], "status": row["status"], "processing": processing}

    def _lookup_policy(self, _: _ClaimId) -> dict[str, Any]:
        row = self._claim_policy()
        return {key: row[key] for key in ("policy_id", "policy_number", "product_line", "policy_status", "start_date", "end_date", "annual_limit", "remaining_limit", "deductible", "riders")}

    def _validate_claim(self, _: _ClaimId) -> dict[str, Any]:
        from app.main import _detect_duplicate_claim, _incident_within_policy
        row, processing = self._claim_policy(), self._processing()
        policy_valid = str(row["policy_status"]).upper() == "ACTIVE" and _incident_within_policy(row["incident_date"], row["start_date"], row["end_date"])
        duplicate = _detect_duplicate_claim(self.claim_id, self.db)["duplicate_detected"]
        sufficient = row["remaining_limit"] is not None and row["remaining_limit"] >= row["claimed_amount"]
        return {"valid": not processing["missing_documents"] and not processing["invalid_documents"] and policy_valid, "documents_complete": processing["complete"], "documents_valid": not processing["invalid_documents"], "missing_documents": processing["missing_documents"], "invalid_documents": processing["invalid_documents"], "duplicate_documents": processing["duplicate_documents"], "consistency": processing["consistency"], "has_conflicts": processing["consistency"]["has_conflicts"], "manual_review_required": processing["manual_review_required"], "policy_valid": policy_valid, "incident_within_policy_period": policy_valid, "remaining_limit_sufficient": sufficient, "duplicate_claim": duplicate, "risk_signals": []}

    def _search_policy_docs(self, args: SearchPolicyDocs) -> dict[str, Any]:
        row = self._claim_policy(); product = (args.product_line or row["product_line"]).upper()
        if product != str(row["product_line"]).upper(): raise ValueError("Product line does not match active claim")
        retriever = HandbookRetriever(ChromaHandbookVectorStore(settings.HANDBOOK_VECTOR_DB_DIR, settings.HANDBOOK_VECTOR_COLLECTION), OpenRouterEmbedder())
        results = retriever.store.query(retriever.embedder.embed([args.query])[0], 6)
        filtered = []
        for item in results:
            meta = item.get("metadata") or {}; applies = str(meta.get("applies_to_products", "ALL")).upper()
            if "ALL" not in applies and product not in applies: continue
            if args.rule_category and str(meta.get("rule_category", "")).upper() != args.rule_category.upper(): continue
            safe = {"chunk_id": item["chunk_id"], "content": str(item.get("content", ""))[:2200], "score": item.get("score"), "metadata": {k: meta.get(k) for k in ("rule_identifier", "section", "chapter", "rule_category", "applies_to_products", "source")}}
            self.retrieved[safe["chunk_id"]] = safe; filtered.append(safe)
        return {"results": filtered[:4]}

    def _approve_or_route_claim(self, args: SubmitRecommendation) -> dict[str, Any]:
        analysis = args.model_dump(); row, processing = self._claim_policy(), self._processing()
        refs = []
        for finding in analysis["reasoning"]:
            for citation in finding.get("handbook_references", []) if isinstance(finding, dict) else []:
                found = self.retrieved.get(str(citation.get("chunk_id"))) if isinstance(citation, dict) else None
                if not found or (citation.get("rule_identifier") and citation["rule_identifier"] != found["metadata"].get("rule_identifier")):
                    raise ValueError("Handbook reference was not returned by search_policy_docs")
                refs.append({"chunk_id": found["chunk_id"], **found["metadata"], "score": found["score"]})
        analysis["retrieved_handbook_references"] = list({x["chunk_id"]: x for x in refs}.values())
        validation = self._validate_claim(_ClaimId(claim_id=self.claim_id))
        preview = decide_claim(claim={"claimed_amount": row["claimed_amount"]}, policy={"status": row["policy_status"], "product_line": row["product_line"], "remaining_limit": row["remaining_limit"], "validation_passed": validation["policy_valid"]}, processing=processing, analysis=analysis, duplicate_detection={"duplicate_detected": validation["duplicate_claim"]}, risk_signals=validation["risk_signals"])
        self.submission = analysis | {"validation": validation, "decision_preview": preview}
        return {"accepted": True, "deterministic_preview": {"final_decision": preview["final_decision"], "reason": preview["reason"]}}

    def _audit(self, name: str, arguments: dict[str, Any], success: bool, started: float) -> None:
        try:
            self.db.execute(text("INSERT INTO audit_logs (claim_id,user_id,action,details) VALUES (:claim_id,:user_id,'LLM_TOOL_CALL',CAST(:details AS jsonb))"), {"claim_id": self.claim_id, "user_id": self.current_user.get("user_id"), "details": json.dumps({"tool": name, "provider": self.provider, "arguments": arguments, "success": success, "duration_ms": round((time.monotonic()-started)*1000, 1)}, default=str)})
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass
