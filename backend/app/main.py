from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.schemas import AuthResponse, LoginRequest, PolicyResponse, RegisterRequest


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


@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.execute(text("SELECT user_id FROM users WHERE email = :email OR national_id = :national_id"), {"email": str(payload.email).lower(), "national_id": payload.national_id}).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or national ID is already registered")
    customer_role = db.execute(text("SELECT role_id FROM roles WHERE role_name = 'Customer'")).mappings().first()
    if customer_role is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Customer role is not configured")
    try:
        user = db.execute(text("INSERT INTO users (full_name, email, password_hash, national_id) VALUES (:full_name, :email, :password_hash, :national_id) RETURNING user_id, full_name, email"), {"full_name": payload.full_name.strip(), "email": str(payload.email).lower(), "password_hash": hash_password(payload.password), "national_id": payload.national_id}).mappings().one()
        db.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"), {"user_id": user["user_id"], "role_id": customer_role["role_id"]})
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
