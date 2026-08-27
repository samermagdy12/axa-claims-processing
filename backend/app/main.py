import json
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import ASSESSOR_ROLE, CUSTOMER_ROLE, OPERATIONS_ROLE, create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.claim_analysis import analyze_claim_context, build_claim_context
from app.claim_analysis_agent import analyze_claim_with_tools
from app.claim_tools import ClaimToolExecutor
from app.claim_analysis_llm import ClaimAnalysisError
from app.decision_engine import decide_claim
from app.claim_requirements import get_required_documents
from app.claim_processing import build_claim_processing_summary, normalize_document_data, present_document_validation, validate_document
from app.config import settings
from app.database import get_db
from app.document_extraction import DocumentExtractionError, extract_document_content
from app.structured_extraction import extract_structured_data
from app.document_upload import store_claim_document
from app.handbook_knowledge import HandbookKnowledgeError
from app.schemas import AssessorDecisionRequest, AuthResponse, ClaimCreateRequest, ClaimCreateResponse, ClaimDocumentUploadResponse, CustomerClaimResponse, DocumentExtractionResponse, LoginRequest, PolicyResponse, PolicyVerificationRequest, RegisterRequest


app = FastAPI(
    title="AXA Claims Processing API",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.FRONTEND_ORIGINS.split(",") if origin.strip()], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "axa-claims-backend",
    }


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }


def serialize_policy(policy: dict) -> dict:
    return {**policy, "riders": policy["riders"] or []}


def get_policies_for_national_id(national_id: str, db: Session) -> list[dict]:
    policies = db.execute(
        text("""
            SELECT p.policy_id, p.policy_number, p.product_line, p.status,
                   p.start_date, p.end_date, p.annual_limit, p.remaining_limit,
                   p.deductible, p.riders
            FROM policies p
            JOIN users u ON u.user_id = p.user_id
            WHERE u.national_id = :national_id
            ORDER BY p.start_date DESC, p.policy_number
        """),
        {"national_id": national_id},
    ).mappings().all()
    return [serialize_policy(dict(policy)) for policy in policies]


@app.post("/auth/verify-policies", response_model=list[PolicyResponse])
def verify_policies(payload: PolicyVerificationRequest, db: Session = Depends(get_db)):
    return get_policies_for_national_id(payload.national_id, db)


@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    existing_email = db.execute(text("SELECT user_id FROM users WHERE email = :email"), {"email": email}).first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or national ID is already registered")
    existing_national_id = db.execute(text("SELECT user_id, email, status FROM users WHERE national_id = :national_id"), {"national_id": payload.national_id}).mappings().first()
    if existing_national_id and (existing_national_id["status"] != "inactive" or not existing_national_id["email"].endswith("@policy-import.local")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or national ID is already registered")
    if not get_policies_for_national_id(payload.national_id, db):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No policies were found for this National ID")
    customer_role = db.execute(text("SELECT role_id FROM roles WHERE role_name = :role_name"), {"role_name": CUSTOMER_ROLE}).mappings().first()
    if customer_role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Customer role is not configured")
    try:
        if existing_national_id:
            user = db.execute(text("UPDATE users SET full_name = :full_name, email = :email, password_hash = :password_hash, status = 'active', updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id RETURNING user_id, full_name, email"), {"user_id": existing_national_id["user_id"], "full_name": payload.full_name.strip(), "email": email, "password_hash": hash_password(payload.password)}).mappings().one()
        else:
            user = db.execute(text("INSERT INTO users (full_name, email, password_hash, national_id) VALUES (:full_name, :email, :password_hash, :national_id) RETURNING user_id, full_name, email"), {"full_name": payload.full_name.strip(), "email": email, "password_hash": hash_password(payload.password), "national_id": payload.national_id}).mappings().one()
        db.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id) ON CONFLICT DO NOTHING"), {"user_id": user["user_id"], "role_id": customer_role["role_id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"access_token": create_access_token(user["user_id"]), "user": {**dict(user), "role": CUSTOMER_ROLE}}


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(text("SELECT u.user_id, u.full_name, u.email, u.password_hash, r.role_name FROM users u JOIN user_roles ur ON ur.user_id = u.user_id JOIN roles r ON r.role_id = ur.role_id WHERE u.email = :email AND u.status = 'active'"), {"email": str(payload.email).lower()}).mappings().first()
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return {"access_token": create_access_token(user["user_id"]), "user": {"user_id": user["user_id"], "full_name": user["full_name"], "email": user["email"], "role": user["role_name"]}}


@app.get("/policies/my", response_model=list[PolicyResponse])
def get_my_policies(current_user: dict = Depends(require_roles(CUSTOMER_ROLE)), db: Session = Depends(get_db)):
    policies = db.execute(text("SELECT policy_id, policy_number, product_line, status, start_date, end_date, annual_limit, remaining_limit, deductible, riders FROM policies WHERE user_id = :user_id ORDER BY start_date DESC, policy_number"), {"user_id": current_user["user_id"]}).mappings().all()
    return [serialize_policy(dict(policy)) for policy in policies]


@app.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(policy_id: str, current_user: dict = Depends(require_roles(CUSTOMER_ROLE)), db: Session = Depends(get_db)):
    policy = db.execute(text("SELECT policy_id, policy_number, product_line, status, start_date, end_date, annual_limit, remaining_limit, deductible, riders FROM policies WHERE policy_id = :policy_id AND user_id = :user_id"), {"policy_id": policy_id, "user_id": current_user["user_id"]}).mappings().first()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this policy")
    return serialize_policy(dict(policy))


@app.get("/claims/my", response_model=list[CustomerClaimResponse])
def get_my_claims(current_user: dict = Depends(require_roles(CUSTOMER_ROLE)), db: Session = Depends(get_db)):
    claims = db.execute(
        text("""
            SELECT c.claim_id, c.policy_id, p.policy_number, p.product_line,
                   c.claim_type, c.incident_date, c.submission_date,
                   c.claimed_amount, c.description, c.status,
                   latest_decision.outcome AS final_decision, latest_decision.reason AS decision_reason,
                   latest_decision.customer_message, latest_decision.handbook_clause, latest_decision.decision_trace
            FROM claims c
            JOIN policies p ON p.policy_id = c.policy_id
            LEFT JOIN LATERAL (
                SELECT outcome, reason, customer_message, handbook_clause, decision_trace FROM decisions
                WHERE claim_id = c.claim_id ORDER BY created_at DESC LIMIT 1
            ) latest_decision ON TRUE
            WHERE p.user_id = :user_id
            ORDER BY c.submission_date DESC, c.created_at DESC
        """),
        {"user_id": current_user["user_id"]},
    ).mappings().all()
    return [_claim_response(dict(claim)) for claim in claims]


@app.get("/claims/{claim_id}", response_model=CustomerClaimResponse)
def get_claim(claim_id: str, current_user: dict = Depends(require_roles(CUSTOMER_ROLE)), db: Session = Depends(get_db)):
    claim = db.execute(
        text("""
            SELECT c.claim_id, c.policy_id, p.policy_number, p.product_line,
                   c.claim_type, c.incident_date, c.submission_date,
                   c.claimed_amount, c.description, c.status,
                   latest_decision.outcome AS final_decision, latest_decision.reason AS decision_reason,
                   latest_decision.customer_message, latest_decision.handbook_clause, latest_decision.decision_trace
            FROM claims c
            JOIN policies p ON p.policy_id = c.policy_id
            LEFT JOIN LATERAL (
                SELECT outcome, reason, customer_message, handbook_clause, decision_trace FROM decisions
                WHERE claim_id = c.claim_id ORDER BY created_at DESC LIMIT 1
            ) latest_decision ON TRUE
            WHERE c.claim_id = :claim_id AND p.user_id = :user_id
        """),
        {"claim_id": claim_id, "user_id": current_user["user_id"]},
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this claim")
    required_documents = db.execute(
        text("""
            SELECT crd.claim_required_document_id, crd.document_type, crd.is_required, crd.status,
                   uploaded_document.original_file_name
            FROM claim_required_documents crd
            LEFT JOIN LATERAL (
                SELECT original_file_name
                FROM claim_documents
                WHERE claim_id = crd.claim_id AND document_type = crd.document_type
                ORDER BY uploaded_at DESC
                LIMIT 1
            ) uploaded_document ON TRUE
            WHERE crd.claim_id = :claim_id
            ORDER BY crd.created_at, crd.document_type
        """),
        {"claim_id": claim_id},
    ).mappings().all()
    return {**_claim_response(dict(claim)), "required_documents": [dict(document) for document in required_documents]}


@app.post("/claims/{claim_id}/documents", response_model=ClaimDocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_claim_document(
    claim_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["role_name"] != CUSTOMER_ROLE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can upload claim documents")
    safe_file_name = Path(file.filename or "").name
    if safe_file_name in {"", ".", ".."}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A file is required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded file is empty")

    claim = db.execute(
        text("SELECT c.claim_id, p.user_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id WHERE c.claim_id = :claim_id"),
        {"claim_id": claim_id},
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if claim["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this claim")

    required_document = db.execute(
        text("SELECT claim_required_document_id, document_type, is_required, status FROM claim_required_documents WHERE claim_id = :claim_id AND document_type = :document_type AND is_required = TRUE"),
        {"claim_id": claim_id, "document_type": document_type},
    ).mappings().first()
    if required_document is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="This document is not required for the claim")
    if required_document["status"] != "MISSING":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This required document has already been uploaded")

    destination = None
    try:
        destination, document_url = store_claim_document(settings.UPLOAD_DIR, claim["claim_id"], safe_file_name, content)
        uploaded_document = db.execute(
            text("""
                INSERT INTO claim_documents (claim_id, document_type, document_url, original_file_name, mime_type, file_size_bytes, uploaded_by)
                VALUES (:claim_id, :document_type, :document_url, :original_file_name, :mime_type, :file_size_bytes, :uploaded_by)
                RETURNING document_id, claim_id, document_type, original_file_name, mime_type, file_size_bytes, uploaded_at
            """),
            {"claim_id": claim_id, "document_type": document_type, "document_url": document_url, "original_file_name": safe_file_name, "mime_type": file.content_type or "application/octet-stream", "file_size_bytes": len(content), "uploaded_by": current_user["user_id"]},
        ).mappings().one()
        required_document = db.execute(
            text("""
                UPDATE claim_required_documents SET status = 'UPLOADED', updated_at = CURRENT_TIMESTAMP
                WHERE claim_required_document_id = :required_document_id
                RETURNING claim_required_document_id, document_type, is_required, status
            """),
            {"required_document_id": required_document["claim_required_document_id"]},
        ).mappings().one()
        missing_count = db.execute(
            text("SELECT COUNT(*) FROM claim_required_documents WHERE claim_id = :claim_id AND is_required = TRUE AND status = 'MISSING'"),
            {"claim_id": claim_id},
        ).scalar_one()
        claim_status = "WAITING_FOR_DOCUMENTS"
        if missing_count == 0:
            claim_status = "PROCESSING"
            db.execute(text("UPDATE claims SET status = :status, updated_at = CURRENT_TIMESTAMP WHERE claim_id = :claim_id"), {"status": claim_status, "claim_id": claim_id})
        db.execute(
            text("INSERT INTO audit_logs (claim_id, user_id, action, details) VALUES (:claim_id, :user_id, 'DOCUMENT_UPLOADED', CAST(:details AS jsonb))"),
            {"claim_id": claim_id, "user_id": current_user["user_id"], "details": json.dumps({"document_type": document_type, "document_id": str(uploaded_document["document_id"])} )},
        )
        db.commit()
    except Exception:
        db.rollback()
        if destination is not None and destination.exists():
            destination.unlink()
        raise
    return {**dict(uploaded_document), "required_document": dict(required_document), "claim_status": claim_status}


@app.delete("/claims/{claim_id}/documents/{document_type:path}")
def remove_claim_document(claim_id: str, document_type: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role_name"] != CUSTOMER_ROLE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can replace claim documents")
    claim = db.execute(
        text("SELECT c.claim_id, p.user_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id WHERE c.claim_id = :claim_id"),
        {"claim_id": claim_id},
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if claim["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this claim")
    document = db.execute(
        text("SELECT document_id, document_url FROM claim_documents WHERE claim_id = :claim_id AND document_type = :document_type ORDER BY uploaded_at DESC LIMIT 1"),
        {"claim_id": claim_id, "document_type": document_type},
    ).mappings().first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        db.execute(text("DELETE FROM claim_extractions WHERE claim_id = :claim_id AND extracted_data ->> 'document_id' = :document_id"), {"claim_id": claim_id, "document_id": str(document["document_id"])})
        db.execute(text("DELETE FROM claim_documents WHERE document_id = :document_id"), {"document_id": document["document_id"]})
        db.execute(text("UPDATE claim_required_documents SET status = 'MISSING', updated_at = CURRENT_TIMESTAMP WHERE claim_id = :claim_id AND document_type = :document_type"), {"claim_id": claim_id, "document_type": document_type})
        db.execute(text("UPDATE claims SET status = 'WAITING_FOR_DOCUMENTS', updated_at = CURRENT_TIMESTAMP WHERE claim_id = :claim_id"), {"claim_id": claim_id})
        db.execute(text("INSERT INTO audit_logs (claim_id, user_id, action, details) VALUES (:claim_id, :user_id, 'DOCUMENT_REMOVED', CAST(:details AS JSONB))"), {"claim_id": claim_id, "user_id": current_user["user_id"], "details": json.dumps({"document_id": str(document["document_id"]), "document_type": document_type})})
        db.commit()
    except Exception:
        db.rollback()
        raise
    document_path = (Path(settings.UPLOAD_DIR).resolve() / document["document_url"]).resolve()
    if document_path.is_relative_to(Path(settings.UPLOAD_DIR).resolve()) and document_path.is_file():
        document_path.unlink()
    return {"document_type": document_type, "status": "removed"}


@app.post("/claims/{claim_id}/documents/{document_id}/extract", response_model=DocumentExtractionResponse)
def extract_claim_document(
    claim_id: str,
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["role_name"] != CUSTOMER_ROLE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can process claim documents")
    claim = db.execute(
        text("SELECT c.claim_id, p.user_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id WHERE c.claim_id = :claim_id"),
        {"claim_id": claim_id},
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if claim["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this claim")
    document = db.execute(
        text("SELECT document_id, claim_id, document_type, document_url, original_file_name, mime_type FROM claim_documents WHERE document_id = :document_id AND claim_id = :claim_id"),
        {"document_id": document_id, "claim_id": claim_id},
    ).mappings().first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    existing = db.execute(
        text("SELECT extraction_id, claim_id, extracted_data, extraction_confidence, extracted_at FROM claim_extractions WHERE claim_id = :claim_id AND extracted_data ->> 'document_id' = :document_id ORDER BY extracted_at DESC LIMIT 1"),
        {"claim_id": claim_id, "document_id": str(document["document_id"])},
    ).mappings().first()
    if existing is not None:
        return _document_extraction_response(dict(existing), reused=True)

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    document_path = (upload_root / document["document_url"]).resolve()
    if not document_path.is_relative_to(upload_root) or not document_path.is_file():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The uploaded file is unavailable")
    try:
        extracted = extract_document_content(document_path, document["mime_type"], document["document_type"])
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    structured_data = extracted.structured_data or extract_structured_data(document["document_type"], extracted.text, extracted.strategy)
    extracted_data = {
        "document_id": str(document["document_id"]),
        "document_type": document["document_type"],
        "original_file_name": document["original_file_name"],
        "processing_strategy": extracted.strategy,
        # Keep the legacy field for existing consumers while making raw text
        # and document-specific parsed fields explicit for future validation.
        "extracted_text": extracted.text,
        "raw_extraction": {"text": extracted.text, **({"document_structure": extracted.structure} if extracted.structure else {})},
        "structured_data": structured_data,
        "normalized_data": normalize_document_data(document["document_type"], structured_data),
        "document_validation": validate_document(document["document_type"], extracted.text, structured_data, mime_type=document["mime_type"], processing_strategy=extracted.strategy),
        "text_length": len(extracted.text),
    }
    try:
        saved = db.execute(
            text("""
                INSERT INTO claim_extractions (claim_id, extracted_data, extraction_confidence)
                VALUES (:claim_id, CAST(:extracted_data AS JSONB), :extraction_confidence)
                RETURNING extraction_id, claim_id, extracted_data, extraction_confidence, extracted_at
            """),
            {"claim_id": claim_id, "extracted_data": json.dumps(extracted_data), "extraction_confidence": extracted.confidence},
        ).mappings().one()
        db.execute(
            text("INSERT INTO audit_logs (claim_id, user_id, action, details) VALUES (:claim_id, :user_id, 'OCR_COMPLETED', CAST(:details AS JSONB))"),
            {"claim_id": claim_id, "user_id": current_user["user_id"], "details": json.dumps({"document_id": str(document["document_id"]), "strategy": extracted.strategy})},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    # Document extraction is the customer-facing trigger.  Once every required
    # document is usable, the rest of the lifecycle proceeds without a button.
    try:
        _run_automatic_pipeline(claim_id, current_user, db)
    except Exception:
        # Extraction has already been committed. A transient RAG/provider or
        # follow-up pipeline failure must not make a valid customer upload look
        # failed; the persisted claim remains available for automatic retry.
        db.rollback()
    return _document_extraction_response(dict(saved), reused=False)


def _document_extraction_response(extraction: dict, reused: bool) -> dict:
    data = extraction["extracted_data"]
    if isinstance(data, str):
        data = json.loads(data)
    return {
        "extraction_id": extraction["extraction_id"],
        "claim_id": extraction["claim_id"],
        "document_id": data["document_id"],
        "document_type": data["document_type"],
        "strategy": data["processing_strategy"],
        "raw_text": data.get("raw_extraction", {}).get("text", data.get("extracted_text", "")),
        "structured_data": data.get("structured_data", {}),
        "validation": present_document_validation(data.get("document_validation")),
        "text_length": data["text_length"],
        "extraction_confidence": extraction["extraction_confidence"],
        "extracted_at": extraction["extracted_at"],
        "reused": reused,
    }


@app.get("/claims/{claim_id}/processing-summary")
def get_claim_processing_summary(claim_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.execute(
        text("SELECT c.claim_id, p.user_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id WHERE c.claim_id = :claim_id"),
        {"claim_id": claim_id},
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if current_user["role_name"] == CUSTOMER_ROLE and claim["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this claim")
    if current_user["role_name"] not in {CUSTOMER_ROLE, ASSESSOR_ROLE, OPERATIONS_ROLE}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to claim processing details")
    required_documents = [dict(row) for row in db.execute(
        text("SELECT document_type, is_required, status FROM claim_required_documents WHERE claim_id = :claim_id ORDER BY created_at, document_type"),
        {"claim_id": claim_id},
    ).mappings().all()]
    uploaded_documents = [dict(row) for row in db.execute(
        text("SELECT document_id, document_type FROM claim_documents WHERE claim_id = :claim_id ORDER BY uploaded_at"),
        {"claim_id": claim_id},
    ).mappings().all()]
    extracted_rows = db.execute(
        text("SELECT extracted_data FROM claim_extractions WHERE claim_id = :claim_id ORDER BY extracted_at"),
        {"claim_id": claim_id},
    ).mappings().all()
    extraction_by_document_id = {}
    for row in extracted_rows:
        data = row["extracted_data"]
        data = json.loads(data) if isinstance(data, str) else data
        if isinstance(data, dict):
            extraction_by_document_id[str(data.get("document_id"))] = data
    documents = []
    for uploaded in uploaded_documents:
        data = extraction_by_document_id.get(str(uploaded["document_id"]))
        if data is None:
            documents.append({"document_id": str(uploaded["document_id"]), "document_type": uploaded["document_type"], "normalized_data": normalize_document_data(uploaded["document_type"], None), "validation": {"expected_document_type": uploaded["document_type"], "detected_document_type": None, "validation_passed": None, "confidence": None, "reason": "Document has not been extracted yet."}})
            continue
        documents.append({"document_id": data.get("document_id"), "document_type": data.get("document_type"), "normalized_data": data.get("normalized_data") or normalize_document_data(data.get("document_type", "Unknown"), data.get("structured_data")), "validation": data.get("document_validation") or validate_document(data.get("document_type", "Unknown"), data.get("extracted_text", ""), data.get("structured_data"))})
    summary = build_claim_processing_summary(required_documents, documents)
    pipeline_row = db.execute(text("SELECT details FROM audit_logs WHERE claim_id = :claim_id AND action = 'AUTOMATED_PIPELINE' ORDER BY timestamp DESC LIMIT 1"), {"claim_id": claim_id}).mappings().first()
    decision_row = db.execute(text("SELECT outcome, reason FROM decisions WHERE claim_id = :claim_id ORDER BY created_at DESC LIMIT 1"), {"claim_id": claim_id}).mappings().first()
    return {**summary, "pipeline": _json_value(pipeline_row["details"]) if pipeline_row else {}, "final_decision": dict(decision_row) if decision_row else None}


@app.post("/claims/{claim_id}/analyze")
def analyze_claim(claim_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Explicitly run the handbook-grounded, provider-fallback claim analysis."""
    if current_user["role_name"] not in {CUSTOMER_ROLE, ASSESSOR_ROLE, OPERATIONS_ROLE}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to claim analysis")
    claim = db.execute(
        text("""SELECT c.claim_id, c.policy_id, c.claim_type, c.incident_date, c.submission_date,
                       c.claimed_amount, c.description, c.status, p.user_id, p.policy_number,
                       p.product_line, p.status AS policy_status, p.start_date, p.end_date,
                       p.annual_limit, p.remaining_limit, p.deductible, p.riders
                FROM claims c JOIN policies p ON p.policy_id = c.policy_id
                WHERE c.claim_id = :claim_id"""),
        {"claim_id": claim_id},
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if current_user["role_name"] == CUSTOMER_ROLE and claim["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this claim")
    required_documents = [dict(row) for row in db.execute(
        text("SELECT document_type, is_required, status FROM claim_required_documents WHERE claim_id = :claim_id ORDER BY created_at, document_type"),
        {"claim_id": claim_id},
    ).mappings().all()]
    uploaded_documents = [dict(row) for row in db.execute(
        text("SELECT document_id, document_type FROM claim_documents WHERE claim_id = :claim_id ORDER BY uploaded_at"),
        {"claim_id": claim_id},
    ).mappings().all()]
    extraction_rows = db.execute(
        text("SELECT extracted_data FROM claim_extractions WHERE claim_id = :claim_id ORDER BY extracted_at"),
        {"claim_id": claim_id},
    ).mappings().all()
    extractions = {}
    for row in extraction_rows:
        data = row["extracted_data"]
        data = json.loads(data) if isinstance(data, str) else data
        if isinstance(data, dict) and data.get("document_id"):
            extractions[str(data["document_id"])] = data
    documents = []
    processing_documents = []
    for document in uploaded_documents:
        extraction = extractions.get(str(document["document_id"]), {})
        validation = extraction.get("document_validation") or {"expected_document_type": document["document_type"], "detected_document_type": None, "validation_passed": None, "reason": "Document has not been extracted yet."}
        documents.append({**document, "extraction": extraction, "validation": validation})
        processing_documents.append({"document_id": str(document["document_id"]), "document_type": document["document_type"], "normalized_data": extraction.get("normalized_data") or normalize_document_data(document["document_type"], extraction.get("structured_data")), "validation": validation})
    processing = build_claim_processing_summary(required_documents, processing_documents)
    claim_data = dict(claim)
    policy = {
        "policy_id": claim_data["policy_id"], "policy_number": claim_data["policy_number"], "product_line": claim_data["product_line"],
        "status": claim_data["policy_status"], "start_date": claim_data["start_date"], "end_date": claim_data["end_date"],
        "annual_limit": claim_data["annual_limit"], "remaining_limit": claim_data["remaining_limit"], "deductible": claim_data["deductible"], "riders": claim_data["riders"],
    }
    policy_valid = str(policy["status"]).upper() == "ACTIVE" and _incident_within_policy(claim_data.get("incident_date"), policy.get("start_date"), policy.get("end_date"))
    policy_validation = {"passed": policy_valid, "reason": "Policy is active and covers the incident date." if policy_valid else "Policy is inactive or does not cover the incident date."}
    # Step 4 is a hard stop: do not call RAG/LLM or imply later stages passed.
    if processing["missing_documents"] or processing["invalid_documents"] or processing["manual_review_required"]:
        return {"claim_id": str(claim_id), "processing": processing, "policy_validation": policy_validation,
                "recommendation": "request_documents", "confidence": 1.0, "summary": "Required documents need attention before policy and coverage checks can continue.",
                "reasoning": [], "missing_information": processing["missing_documents"], "validation_issues": [item.get("document_type") for item in processing["invalid_documents"]],
                "consistency_issues": [], "recommended_next_actions": ["Provide or replace the required documents."], "retrieved_handbook_references": [], "retrieval": {"results": []}, "provider": "deterministic"}
    try:
        # The analysis model receives only the active claim ID initially and
        # dynamically requests authorized evidence through real tool calls.
        analysis = analyze_claim_with_tools(ClaimToolExecutor(claim_id, current_user, db))
    except (HandbookKnowledgeError, ClaimAnalysisError) as exc:
        # Never leave a complete customer claim in limbo because an external
        # reasoning provider is unavailable. The deterministic engine will
        # conservatively route it to an assessor instead of fabricating cover.
        analysis = {"recommendation": "route_to_human", "confidence": 0.0,
                    "summary": "Automated coverage analysis is unavailable; specialist review is required.",
                    "reasoning": [], "missing_information": [], "validation_issues": [], "consistency_issues": [],
                    "recommended_next_actions": ["Assign an assessor."], "retrieved_handbook_references": [],
                    "retrieval": {"results": []}, "provider": "deterministic_fallback"}
    return {"claim_id": str(claim_id), "processing": processing, "policy_validation": policy_validation, **analysis}


@app.post("/claims/{claim_id}/decide")
def decide_claim_endpoint(claim_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Internal-compatible entry point; customer flow invokes this automatically."""
    return _run_automatic_pipeline(claim_id, current_user, db)


def _run_automatic_pipeline(claim_id: str, current_user: dict, db: Session) -> dict:
    """Persist the deterministic lifecycle after documents are extracted."""
    analysis_result = analyze_claim(claim_id, current_user, db)
    claim = db.execute(
        text("""SELECT c.claim_id, c.claimed_amount, c.incident_date, p.status AS policy_status, p.product_line, p.start_date, p.end_date
                 FROM claims c JOIN policies p ON p.policy_id = c.policy_id
                 WHERE c.claim_id = :claim_id"""), {"claim_id": claim_id}
    ).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    duplicate_detection = _detect_duplicate_claim(claim_id, db)
    policy_for_decision = {
        "status": claim["policy_status"],
        "product_line": claim["product_line"],
        "start_date": claim["start_date"], "end_date": claim["end_date"],
        "remaining_limit": analysis_result.get("policy", {}).get("remaining_limit"),
        "validation_passed": (analysis_result.get("policy_validation") or {}).get("passed", False),
    }
    # The analysis response deliberately exposes only policy-validation state;
    # load the actual remaining limit for deterministic settlement gating.
    policy_row = db.execute(text("SELECT remaining_limit FROM policies p JOIN claims c ON c.policy_id = p.policy_id WHERE c.claim_id = :claim_id"), {"claim_id": claim_id}).mappings().first()
    policy_for_decision["remaining_limit"] = policy_row["remaining_limit"] if policy_row else None
    result = decide_claim(claim=dict(claim), policy=policy_for_decision, processing=analysis_result["processing"], analysis=analysis_result, duplicate_detection=duplicate_detection)
    claim_status = {"settle": "APPROVED", "request_documents": "WAITING_FOR_DOCUMENTS", "reject": "REJECTED", "route_to_human": "UNDER_HUMAN_REVIEW"}[result["final_decision"]]
    handbook_clause = next((reference.get("rule_identifier") for reference in result["handbook_references"] if reference.get("rule_identifier")), None)
    try:
        triggered = {rule["rule_id"] for rule in result["triggered_rules"]}
        stage_state = {
            "required_documents": "blocked" if result["final_decision"] == "request_documents" else "completed",
            "policy_validation": "failed" if "POLICY_VALIDATION_FAILED" in triggered else "completed" if result["final_decision"] != "request_documents" else "waiting",
            "coverage_check": "failed" if "COVERAGE_EXCLUSION_SUPPORTED" in triggered else "completed" if result["final_decision"] != "request_documents" else "waiting",
            "risk_check": "review_required" if result["human_review_required"] else "completed" if result["final_decision"] != "request_documents" else "waiting",
            "decision": "completed",
            "policy_validation_detail": analysis_result.get("policy_validation"),
        }
        db.execute(text("UPDATE claims SET status = :status, updated_at = CURRENT_TIMESTAMP WHERE claim_id = :claim_id"), {"status": claim_status, "claim_id": claim_id})
        db.execute(text("""INSERT INTO decisions (claim_id, outcome, reason, decision_trace, handbook_clause, risk_detected, risk_reason, customer_message)
                         VALUES (:claim_id, :outcome, :reason, CAST(:decision_trace AS jsonb), :handbook_clause, :risk_detected, :risk_reason, :customer_message)"""), {
            "claim_id": claim_id, "outcome": result["final_decision"], "reason": result["reason"], "decision_trace": json.dumps(result["decision_trace"], default=str), "handbook_clause": handbook_clause,
            "risk_detected": result["human_review_required"], "risk_reason": result["reason"] if result["human_review_required"] else None,
            "customer_message": result["customer_message"],
        })
        db.execute(text("""INSERT INTO audit_logs (claim_id, user_id, action, details)
                         VALUES (:claim_id, :user_id, 'FINAL_DECISION', CAST(:details AS jsonb))"""), {
            "claim_id": claim_id, "user_id": current_user["user_id"], "details": json.dumps(result, default=str),
        })
        db.execute(text("""INSERT INTO audit_logs (claim_id, user_id, action, details)
                         VALUES (:claim_id, :user_id, 'AUTOMATED_PIPELINE', CAST(:details AS jsonb))"""), {
            "claim_id": claim_id, "user_id": current_user["user_id"], "details": json.dumps(stage_state, default=str),
        })
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"claim_id": str(claim_id), **result}


def _incident_within_policy(incident_date, start_date, end_date) -> bool:
    try:
        incident = date.fromisoformat(str(incident_date)[:10])
        return date.fromisoformat(str(start_date)[:10]) <= incident <= date.fromisoformat(str(end_date)[:10])
    except (TypeError, ValueError):
        return False


def _detect_duplicate_claim(claim_id: str, db: Session) -> dict[str, bool]:
    """Check actual prior claims, not merely duplicate uploaded document types."""
    duplicate = db.execute(text("""
        SELECT EXISTS(
          SELECT 1 FROM claims candidate
          JOIN claims current_claim ON current_claim.claim_id = :claim_id
          WHERE candidate.claim_id <> current_claim.claim_id
            AND candidate.policy_id = current_claim.policy_id
            AND candidate.claim_type = current_claim.claim_type
            AND candidate.incident_date = current_claim.incident_date
            AND candidate.claimed_amount = current_claim.claimed_amount
        ) AS duplicate_detected
    """), {"claim_id": claim_id}).mappings().first()
    return {"duplicate_detected": bool(duplicate and duplicate["duplicate_detected"])}


def _claim_response(claim: dict) -> dict:
    final = claim.pop("final_decision", None)
    if final:
        claim["final_decision"] = {
            "final_decision": final,
            "reason": claim.pop("decision_reason", None),
            "customer_message": claim.pop("customer_message", None),
            "handbook_clause": claim.pop("handbook_clause", None),
            "decision_trace": _json_value(claim.pop("decision_trace", None)),
        }
    else:
        claim.pop("decision_reason", None)
        claim.pop("customer_message", None)
        claim.pop("handbook_clause", None)
    return claim


@app.post("/claims", response_model=ClaimCreateResponse, status_code=status.HTTP_201_CREATED)
def create_claim(payload: ClaimCreateRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role_name"] != CUSTOMER_ROLE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can create claims")

    policy = db.execute(
        text("SELECT policy_id, user_id, product_line FROM policies WHERE policy_id = :policy_id"),
        {"policy_id": payload.policy_id},
    ).mappings().first()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if policy["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this policy")

    required_document_types = get_required_documents(policy["product_line"], payload.claim_type)
    if required_document_types is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Claim type is not supported for this policy")

    try:
        claim = db.execute(
            text("""
                INSERT INTO claims (policy_id, claim_type, incident_date, claimed_amount, description, status)
                VALUES (:policy_id, :claim_type, :incident_date, :claimed_amount, :description, 'WAITING_FOR_DOCUMENTS')
                RETURNING claim_id, policy_id, claim_type, incident_date, submission_date, claimed_amount, description, status
            """),
            payload.model_dump(),
        ).mappings().one()
        required_documents = []
        for document_type in required_document_types:
            required_document = db.execute(
                text("""
                    INSERT INTO claim_required_documents (claim_id, document_type, is_required, status)
                    VALUES (:claim_id, :document_type, TRUE, 'MISSING')
                    RETURNING claim_required_document_id, document_type, is_required, status
                """),
                {"claim_id": claim["claim_id"], "document_type": document_type},
            ).mappings().one()
            required_documents.append(dict(required_document))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {**dict(claim), "required_documents": required_documents}


@app.get("/internal/assessor")
def assessor_area(current_user: dict = Depends(require_roles(ASSESSOR_ROLE))):
    """Minimal protected entry point for future assessor review workflows."""
    return {"role": current_user["role_name"], "message": "Assessor access granted"}


@app.get("/assessor/claims")
def assessor_review_queue(current_user: dict = Depends(require_roles(ASSESSOR_ROLE)), db: Session = Depends(get_db)):
    """Claims that have been deterministically routed for human action."""
    rows = db.execute(text("""
        SELECT c.claim_id, c.claim_type, c.claimed_amount, c.incident_date, c.submission_date, c.status,
               u.full_name AS customer_name, p.policy_number, p.product_line,
               d.outcome AS final_decision, d.reason, d.risk_detected,
               hr.human_decision
        FROM claims c JOIN policies p ON p.policy_id = c.policy_id JOIN users u ON u.user_id = p.user_id
        LEFT JOIN LATERAL (SELECT outcome, reason, risk_detected FROM decisions WHERE claim_id = c.claim_id ORDER BY created_at DESC LIMIT 1) d ON TRUE
        LEFT JOIN LATERAL (SELECT human_decision FROM human_reviews WHERE claim_id = c.claim_id ORDER BY reviewed_at DESC NULLS LAST LIMIT 1) hr ON TRUE
        WHERE c.status IN ('UNDER_HUMAN_REVIEW', 'ROUTED', 'ESCALATED') AND hr.human_decision IS NULL
        ORDER BY c.submission_date ASC
    """)).mappings().all()
    return [{**dict(row), "risk_level": "HIGH" if row["risk_detected"] else "MEDIUM" if row["final_decision"] == "route_to_human" else "NONE"} for row in rows]


@app.get("/assessor/claims/{claim_id}")
def assessor_claim_review(claim_id: str, current_user: dict = Depends(require_roles(ASSESSOR_ROLE)), db: Session = Depends(get_db)):
    claim = db.execute(text("""
        SELECT c.claim_id, c.policy_id, c.claim_type, c.incident_date, c.submission_date, c.claimed_amount, c.description, c.status,
               u.full_name AS customer_name, p.policy_number, p.product_line, p.status AS policy_status,
               p.start_date, p.end_date, p.annual_limit, p.remaining_limit, p.deductible, p.riders,
               d.outcome AS final_decision, d.reason AS final_reason, d.customer_message, d.handbook_clause, d.risk_detected,
               hr.ai_recommendation, hr.human_decision, hr.review_reason, hr.reviewed_at
        FROM claims c JOIN policies p ON p.policy_id = c.policy_id JOIN users u ON u.user_id = p.user_id
        LEFT JOIN LATERAL (SELECT outcome, reason, customer_message, handbook_clause, risk_detected FROM decisions WHERE claim_id = c.claim_id ORDER BY created_at DESC LIMIT 1) d ON TRUE
        LEFT JOIN LATERAL (SELECT ai_recommendation, human_decision, review_reason, reviewed_at FROM human_reviews WHERE claim_id = c.claim_id ORDER BY reviewed_at DESC NULLS LAST LIMIT 1) hr ON TRUE
        WHERE c.claim_id = :claim_id
    """), {"claim_id": claim_id}).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    documents = [dict(row) for row in db.execute(text("""
        SELECT cd.document_id, cd.document_type, cd.original_file_name, cd.mime_type, cd.file_size_bytes, cd.uploaded_at,
               ce.extraction_confidence, ce.extracted_data
        FROM claim_documents cd LEFT JOIN LATERAL (
            SELECT extraction_confidence, extracted_data FROM claim_extractions
            WHERE claim_id = cd.claim_id AND extracted_data ->> 'document_id' = cd.document_id::text
            ORDER BY extracted_at DESC LIMIT 1
        ) ce ON TRUE WHERE cd.claim_id = :claim_id ORDER BY cd.uploaded_at
    """), {"claim_id": claim_id}).mappings().all()]
    audit = [dict(row) for row in db.execute(text("""
        SELECT al.timestamp, al.action, al.details, COALESCE(u.full_name, 'System') AS actor
        FROM audit_logs al LEFT JOIN users u ON u.user_id = al.user_id
        WHERE al.claim_id = :claim_id ORDER BY al.timestamp ASC
    """), {"claim_id": claim_id}).mappings().all()]
    final_audit = next((row for row in reversed(audit) if row["action"] == "FINAL_DECISION"), None)
    final_details = _json_value(final_audit.get("details")) if final_audit else {}
    return {"claim": dict(claim), "documents": [_assessor_document(row) for row in documents], "audit_trail": [_audit_entry(row) for row in audit],
            "llm_recommendation": final_details.get("llm_recommendation") or claim["ai_recommendation"],
            "triggered_rules": final_details.get("triggered_rules", []), "handbook_references": final_details.get("handbook_references", []),
            "processing": final_details.get("processing", {})}


@app.post("/assessor/claims/{claim_id}/decision")
def submit_assessor_decision(claim_id: str, payload: AssessorDecisionRequest, current_user: dict = Depends(require_roles(ASSESSOR_ROLE)), db: Session = Depends(get_db)):
    reason = (payload.reason or "").strip()
    if payload.requires_reason() and not reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A reason is required for rejection or override")
    if payload.action == "override" and not payload.override_decision:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="An override decision is required")
    claim = db.execute(text("""SELECT c.claim_id, c.status, d.outcome AS final_decision,
        (SELECT details ->> 'llm_recommendation' FROM audit_logs WHERE claim_id = c.claim_id AND action = 'FINAL_DECISION' ORDER BY timestamp DESC LIMIT 1) AS llm_recommendation
        FROM claims c LEFT JOIN LATERAL (SELECT outcome FROM decisions WHERE claim_id = c.claim_id ORDER BY created_at DESC LIMIT 1) d ON TRUE WHERE c.claim_id = :claim_id"""), {"claim_id": claim_id}).mappings().first()
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if claim["status"] not in {"UNDER_HUMAN_REVIEW", "ROUTED", "ESCALATED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This claim is not awaiting assessor action")
    decision = payload.override_decision if payload.action == "override" else payload.action
    status_by_decision = {"settle": "APPROVED", "reject": "REJECTED", "route_to_human": "ESCALATED"}
    try:
        db.execute(text("UPDATE claims SET status = :status, updated_at = CURRENT_TIMESTAMP WHERE claim_id = :claim_id"), {"status": status_by_decision[decision], "claim_id": claim_id})
        db.execute(text("""INSERT INTO human_reviews (claim_id, assessor_id, ai_recommendation, human_decision, review_reason, reviewed_at)
                         VALUES (:claim_id, :assessor_id, :ai_recommendation, :human_decision, :reason, CURRENT_TIMESTAMP)"""),
                   {"claim_id": claim_id, "assessor_id": current_user["user_id"], "ai_recommendation": claim["llm_recommendation"], "human_decision": decision, "reason": reason or None})
        db.execute(text("""INSERT INTO decisions (claim_id, outcome, reason, customer_message, decided_by)
                         VALUES (:claim_id, :outcome, :reason, :customer_message, :assessor_id)"""),
                   {"claim_id": claim_id, "outcome": decision, "reason": reason or "Assessor decision recorded.", "assessor_id": current_user["user_id"], "customer_message": _customer_message_for_human_decision(decision)})
        db.execute(text("""INSERT INTO audit_logs (claim_id, user_id, action, details)
                         VALUES (:claim_id, :user_id, :action, CAST(:details AS jsonb))"""),
                   {"claim_id": claim_id, "user_id": current_user["user_id"], "action": "ASSESSOR_OVERRIDE" if payload.action == "override" else "ASSESSOR_DECISION", "details": json.dumps({"action": payload.action, "decision": decision, "reason": reason, "original_llm_recommendation": claim["llm_recommendation"], "previous_final_decision": claim["final_decision"]})})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"claim_id": str(claim_id), "human_decision": decision, "decision_source": "human", "reason": reason}


@app.get("/operations/overview")
def operations_overview(current_user: dict = Depends(require_roles(OPERATIONS_ROLE)), db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT p.product_line,
          COUNT(*) AS processed,
          COUNT(*) FILTER (WHERE c.status = 'APPROVED') AS approved,
          COUNT(*) FILTER (WHERE c.status IN ('UNDER_HUMAN_REVIEW', 'ROUTED', 'ESCALATED')) AS routed,
          COUNT(*) FILTER (WHERE c.status = 'REJECTED') AS rejected,
          COUNT(*) FILTER (WHERE d.risk_detected) AS risk_flagged
        FROM claims c JOIN policies p ON p.policy_id = c.policy_id
        LEFT JOIN LATERAL (SELECT risk_detected FROM decisions WHERE claim_id = c.claim_id ORDER BY created_at DESC LIMIT 1) d ON TRUE
        GROUP BY p.product_line ORDER BY p.product_line
    """)).mappings().all()
    return {"product_lines": [dict(row) for row in rows]}


def _json_value(value):
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value) if value else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _assessor_document(row: dict) -> dict:
    extracted = _json_value(row.get("extracted_data"))
    validation = extracted.get("document_validation") or {}
    return {"document_id": str(row["document_id"]), "document_type": row["document_type"], "file_name": row["original_file_name"], "mime_type": row["mime_type"], "file_size_bytes": row["file_size_bytes"], "uploaded_at": row["uploaded_at"], "confidence": row["extraction_confidence"], "structured_data": extracted.get("structured_data", {}), "validation": validation}


def _audit_entry(row: dict) -> dict:
    details = _json_value(row.get("details"))
    return {"timestamp": row["timestamp"], "action": row["action"], "actor": row["actor"], "details": details if isinstance(details, str) else json.dumps(details, default=str)}


def _customer_message_for_human_decision(decision: str) -> str:
    return {"settle": "Your claim has been approved and will proceed to settlement.", "reject": "We are unable to approve this claim. Please review the decision details for the applicable reason.", "route_to_human": "Your claim has been escalated for further specialist review."}[decision]


@app.get("/internal/operations")
def operations_area(current_user: dict = Depends(require_roles(OPERATIONS_ROLE))):
    """Minimal protected entry point for future operations workflows."""
    return {"role": current_user["role_name"], "message": "Operations access granted"}
