CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    full_name VARCHAR(150) NOT NULL,

    email VARCHAR(255) NOT NULL UNIQUE,

    password_hash TEXT NOT NULL,

    national_id VARCHAR(50) NOT NULL UNIQUE,

    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    role_name VARCHAR(50) NOT NULL UNIQUE,

    description TEXT
);

INSERT INTO roles (role_name, description)
VALUES
    ('Customer', 'Customer who submits and tracks insurance claims'),
    ('Assessor', 'AXA assessor who reviews routed claims'),
    ('Operations', 'Operations user who views claim statistics and product-line counts');

SELECT * FROM roles;

CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,

    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, role_id),

    CONSTRAINT fk_user_roles_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_roles_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
        ON DELETE CASCADE
);

CREATE TABLE policies (
    policy_id VARCHAR(50) PRIMARY KEY,

    user_id UUID NOT NULL,

    policy_number VARCHAR(100) UNIQUE NOT NULL,

    product_line VARCHAR(20) NOT NULL
        CHECK (product_line IN ('HEALTH', 'MOTOR', 'PROPERTY', 'TRAVEL')),

    status VARCHAR(20) NOT NULL
        CHECK (status IN ('ACTIVE', 'LAPSED', 'CANCELLED', 'PENDING')),

    start_date DATE NOT NULL,

    end_date DATE NOT NULL,

    annual_limit NUMERIC(12,2) NOT NULL
        CHECK (annual_limit >= 0),

    remaining_limit NUMERIC(12,2) NOT NULL
        CHECK (remaining_limit >= 0),

    deductible NUMERIC(12,2) NOT NULL DEFAULT 0
        CHECK (deductible >= 0),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_policies_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT,

    CONSTRAINT chk_policy_dates
        CHECK (end_date >= start_date),

    CONSTRAINT chk_remaining_limit
        CHECK (remaining_limit <= annual_limit)
);

CREATE TABLE policy_riders (
    policy_rider_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    policy_id VARCHAR(50) NOT NULL,

    rider_type VARCHAR(50) NOT NULL,

    start_date DATE NOT NULL,

    end_date DATE,

    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'INACTIVE')),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_policy_riders_policy
        FOREIGN KEY (policy_id)
        REFERENCES policies(policy_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_policy_rider
        UNIQUE (policy_id, rider_type)
);

CREATE TABLE claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    policy_id VARCHAR(50) NOT NULL,

    claim_type VARCHAR(50) NOT NULL,

    incident_date DATE NOT NULL,

    submission_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    claimed_amount NUMERIC(12,2) NOT NULL
        CHECK (claimed_amount >= 0),

    description TEXT,

    status VARCHAR(40) NOT NULL DEFAULT 'PROCESSING'
        CHECK (
            status IN (
                'PROCESSING',
                'WAITING_FOR_DOCUMENTS',
                'UNDER_HUMAN_REVIEW',
                'APPROVED',
                'REJECTED',
                'ROUTED',
                'ESCALATED',
                'BELOW_DEDUCTIBLE',
                'CLOSED'
            )
        ),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_claims_policy
        FOREIGN KEY (policy_id)
        REFERENCES policies(policy_id)
        ON DELETE RESTRICT
);

CREATE TABLE claim_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    claim_id UUID NOT NULL,

    document_type VARCHAR(100) NOT NULL,

    document_url TEXT NOT NULL,

    original_file_name VARCHAR(255) NOT NULL,

    mime_type VARCHAR(100) NOT NULL,

    file_size_bytes BIGINT,

    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    uploaded_by UUID NOT NULL,

    CONSTRAINT fk_claim_documents_claim
        FOREIGN KEY (claim_id)
        REFERENCES claims(claim_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_claim_documents_user
        FOREIGN KEY (uploaded_by)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

CREATE TABLE claim_required_documents (
    claim_required_document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    claim_id UUID NOT NULL,

    document_type VARCHAR(100) NOT NULL,

    is_required BOOLEAN NOT NULL DEFAULT TRUE,

    status VARCHAR(20) NOT NULL DEFAULT 'MISSING'
        CHECK (status IN ('MISSING', 'UPLOADED', 'VERIFIED')),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_claim_required_documents_claim
        FOREIGN KEY (claim_id)
        REFERENCES claims(claim_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_claim_required_document
        UNIQUE (claim_id, document_type)
);

CREATE TABLE claim_extractions (
    extraction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    claim_id UUID NOT NULL,

    extracted_data JSONB NOT NULL,

    extraction_confidence NUMERIC(5,4),

    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_claim_extractions_claim
        FOREIGN KEY (claim_id)
        REFERENCES claims(claim_id)
        ON DELETE CASCADE
);

CREATE TABLE decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    claim_id UUID NOT NULL,

    outcome VARCHAR(50) NOT NULL,

    reason TEXT,

    decision_trace JSONB,

    handbook_clause VARCHAR(50),

    risk_detected BOOLEAN NOT NULL DEFAULT FALSE,

    risk_reason TEXT,

    customer_message TEXT,

    decided_by UUID,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_decisions_claim
        FOREIGN KEY (claim_id)
        REFERENCES claims(claim_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_decisions_user
        FOREIGN KEY (decided_by)
        REFERENCES users(user_id)
        ON DELETE SET NULL
);

CREATE TABLE human_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    claim_id UUID NOT NULL,

    assessor_id UUID NOT NULL,

    ai_recommendation VARCHAR(50),

    human_decision VARCHAR(50),

    review_reason TEXT,

    reviewed_at TIMESTAMP,

    CONSTRAINT fk_human_reviews_claim
        FOREIGN KEY (claim_id)
        REFERENCES claims(claim_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_human_reviews_assessor
        FOREIGN KEY (assessor_id)
        REFERENCES users(user_id)
        ON DELETE RESTRICT
);

CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    claim_id UUID NOT NULL,

    user_id UUID,

    action VARCHAR(100) NOT NULL,

    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    details JSONB,

    CONSTRAINT fk_audit_logs_claim
        FOREIGN KEY (claim_id)
        REFERENCES claims(claim_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_audit_logs_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
);

ALTER TABLE policies
ADD COLUMN riders JSONB NOT NULL DEFAULT '[]'::jsonb;

DROP TABLE IF EXISTS policy_riders;
