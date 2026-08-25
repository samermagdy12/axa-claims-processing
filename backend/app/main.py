import json
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import ASSESSOR_ROLE, CUSTOMER_ROLE, OPERATIONS_ROLE, create_access_token, get_current_user, hash_password, require_roles, verify_password
from app.claim_requirements import get_required_documents
from app.config import settings
from app.database import get_db
from app.document_extraction import DocumentExtractionError, extract_document_content
from app.structured_extraction import extract_structured_data
from app.document_upload import store_claim_document
from app.schemas import AuthResponse, ClaimCreateRequest, ClaimCreateResponse, ClaimDocumentUploadResponse, CustomerClaimResponse, DocumentExtractionResponse, LoginRequest, PolicyResponse, PolicyVerificationRequest, RegisterRequest


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
                   c.claimed_amount, c.description, c.status
            FROM claims c
            JOIN policies p ON p.policy_id = c.policy_id
            WHERE p.user_id = :user_id
            ORDER BY c.submission_date DESC, c.created_at DESC
        """),
        {"user_id": current_user["user_id"]},
    ).mappings().all()
    return [dict(claim) for claim in claims]


@app.get("/claims/{claim_id}", response_model=CustomerClaimResponse)
def get_claim(claim_id: str, current_user: dict = Depends(require_roles(CUSTOMER_ROLE)), db: Session = Depends(get_db)):
    claim = db.execute(
        text("""
            SELECT c.claim_id, c.policy_id, p.policy_number, p.product_line,
                   c.claim_type, c.incident_date, c.submission_date,
                   c.claimed_amount, c.description, c.status
            FROM claims c
            JOIN policies p ON p.policy_id = c.policy_id
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
    return {**dict(claim), "required_documents": [dict(document) for document in required_documents]}


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

    extracted_data = {
        "document_id": str(document["document_id"]),
        "document_type": document["document_type"],
        "original_file_name": document["original_file_name"],
        "processing_strategy": extracted.strategy,
        # Keep the legacy field for existing consumers while making raw text
        # and document-specific parsed fields explicit for future validation.
        "extracted_text": extracted.text,
        "raw_extraction": {"text": extracted.text},
        "structured_data": extract_structured_data(document["document_type"], extracted.text, extracted.strategy),
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
        "text_length": data["text_length"],
        "extraction_confidence": extraction["extraction_confidence"],
        "extracted_at": extraction["extracted_at"],
        "reused": reused,
    }


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


@app.get("/internal/operations")
def operations_area(current_user: dict = Depends(require_roles(OPERATIONS_ROLE))):
    """Minimal protected entry point for future operations workflows."""
    return {"role": current_user["role_name"], "message": "Operations access granted"}
