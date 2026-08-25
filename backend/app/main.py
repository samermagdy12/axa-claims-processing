from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.claim_requirements import get_required_documents
from app.config import settings
from app.database import get_db
from app.schemas import AuthResponse, ClaimCreateRequest, ClaimCreateResponse, CustomerClaimResponse, LoginRequest, PolicyResponse, PolicyVerificationRequest, RegisterRequest


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
    customer_role = db.execute(text("SELECT role_id FROM roles WHERE role_name = 'Customer'")).mappings().first()
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
    return {"access_token": create_access_token(user["user_id"]), "user": {**dict(user), "role": "Customer"}}


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(text("SELECT u.user_id, u.full_name, u.email, u.password_hash, r.role_name FROM users u JOIN user_roles ur ON ur.user_id = u.user_id JOIN roles r ON r.role_id = ur.role_id WHERE u.email = :email AND u.status = 'active'"), {"email": str(payload.email).lower()}).mappings().first()
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return {"access_token": create_access_token(user["user_id"]), "user": {"user_id": user["user_id"], "full_name": user["full_name"], "email": user["email"], "role": user["role_name"]}}


@app.get("/policies/my", response_model=list[PolicyResponse])
def get_my_policies(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    policies = db.execute(text("SELECT policy_id, policy_number, product_line, status, start_date, end_date, annual_limit, remaining_limit, deductible, riders FROM policies WHERE user_id = :user_id ORDER BY start_date DESC, policy_number"), {"user_id": current_user["user_id"]}).mappings().all()
    return [serialize_policy(dict(policy)) for policy in policies]


@app.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(policy_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    policy = db.execute(text("SELECT policy_id, policy_number, product_line, status, start_date, end_date, annual_limit, remaining_limit, deductible, riders FROM policies WHERE policy_id = :policy_id AND user_id = :user_id"), {"policy_id": policy_id, "user_id": current_user["user_id"]}).mappings().first()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this policy")
    return serialize_policy(dict(policy))


@app.get("/claims/my", response_model=list[CustomerClaimResponse])
def get_my_claims(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
def get_claim(claim_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
            SELECT claim_required_document_id, document_type, is_required, status
            FROM claim_required_documents
            WHERE claim_id = :claim_id
            ORDER BY created_at, document_type
        """),
        {"claim_id": claim_id},
    ).mappings().all()
    return {**dict(claim), "required_documents": [dict(document) for document in required_documents]}


@app.post("/claims", response_model=ClaimCreateResponse, status_code=status.HTTP_201_CREATED)
def create_claim(payload: ClaimCreateRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role_name"] != "Customer":
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
