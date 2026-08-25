from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8)
    national_id: str = Field(min_length=1, max_length=50)


class PolicyVerificationRequest(BaseModel):
    national_id: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    # Internal AXA accounts use the controlled .local domain.
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    policy_id: str
    policy_number: str
    product_line: str
    status: str
    start_date: date
    end_date: date
    annual_limit: Decimal
    remaining_limit: Decimal
    deductible: Decimal
    riders: list[str]


class ClaimCreateRequest(BaseModel):
    policy_id: str = Field(min_length=1, max_length=50)
    claim_type: str = Field(min_length=1, max_length=50)
    incident_date: date
    claimed_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=20)


class RequiredDocumentResponse(BaseModel):
    claim_required_document_id: UUID
    document_type: str
    is_required: bool
    status: str
    original_file_name: str | None = None


class ClaimCreateResponse(BaseModel):
    claim_id: UUID
    policy_id: str
    claim_type: str
    incident_date: date
    submission_date: datetime
    claimed_amount: Decimal
    description: str | None
    status: str
    required_documents: list[RequiredDocumentResponse]


class CustomerClaimResponse(BaseModel):
    claim_id: UUID
    policy_id: str
    policy_number: str
    product_line: str
    claim_type: str
    incident_date: date
    submission_date: datetime
    claimed_amount: Decimal
    description: str | None
    status: str
    required_documents: list[RequiredDocumentResponse] = Field(default_factory=list)


class ClaimDocumentUploadResponse(BaseModel):
    document_id: UUID
    claim_id: UUID
    document_type: str
    original_file_name: str
    mime_type: str
    file_size_bytes: int
    uploaded_at: datetime
    required_document: RequiredDocumentResponse
    claim_status: str


class DocumentExtractionResponse(BaseModel):
    extraction_id: UUID
    claim_id: UUID
    document_id: UUID
    document_type: str
    strategy: str
    text_length: int
    extraction_confidence: Decimal | None
    extracted_at: datetime
    reused: bool
