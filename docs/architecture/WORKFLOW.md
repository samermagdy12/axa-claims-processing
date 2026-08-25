# AXA Claims Processing Platform
## Claim Processing Workflow

This document describes the end-to-end business workflow for processing an insurance claim.

The workflow supports four insurance product lines:

- Health
- Motor
- Property
- Travel

The system has three user roles:

- Customer
- Assessor
- Operations

Human Review is a workflow state and queue. It is not a separate user role.

---

## 1. Customer Authentication

The customer starts at the Login page.

The customer provides:

- Email
- Password

The backend authenticates the customer.

If authentication fails:

```text
Login
  ↓
Authentication Failed
  ↓
Show authentication error
```

If authentication succeeds:

```text
Login
  ↓
Load customer policies
```

---

## 2. Customer Policy Selection

After login, the backend retrieves the policies linked to the authenticated customer.

The customer selects one of their policies.

The customer does not manually enter a Policy ID.

The backend validates that the selected policy belongs to the authenticated customer.

### Invalid Policy

If the selected policy is not linked to the customer:

```text
Invalid policy selection
        ↓
"Invalid policy selection.
This policy is not linked to your account."
```

The claim cannot continue.

### Valid Policy

```text
Customer
   ↓
Select owned policy
   ↓
Ownership validation
   ↓
Create claim
```

---

## 3. Claim Creation

The customer creates a claim against the selected policy.

The customer provides the claim description using a text field.

The customer uploads the available claim documents.

The selected policy determines which documents are required for the claim type.

The customer does not need to know the internal processing logic.

---

## 4. Document Storage

Each uploaded document is stored with its claim and metadata.

The system stores:

- Document type
- File URL
- Original file name
- MIME type
- File size
- Upload timestamp
- User who uploaded the document

The document itself is stored outside the database.

The database stores the document URL and metadata.

```text
Customer
   ↓
Upload document
   ↓
Document storage
   ↓
Document URL + metadata
   ↓
Claim processing
```

---

## 5. OCR and Document Processing

The uploaded claim documents are passed to the document-processing pipeline.

```text
Uploaded Documents
        ↓
OCR / Vision
        ↓
Claim Text
        ↓
Claim Data Extraction
```

The system extracts relevant claim information.

Examples include:

- Claim type
- Incident date
- Claimed amount
- Medical information
- Vehicle information
- Property information
- Travel information
- Other relevant claim details

The extracted information is stored against the claim.

---

## 6. Claim Type Identification

The system identifies the claim type.

The claim type determines the required-document rules and the relevant policy coverage rules.

Examples:

```text
HEALTH
  ├── Inpatient
  ├── Medication
  └── Diagnostics

MOTOR
  ├── Collision
  ├── Theft
  └── Third-party

PROPERTY
  ├── Fire / Damage
  └── Theft

TRAVEL
  ├── Medical
  ├── Cancellation
  └── Baggage
```

---

## 7. Required Documents Check

After identifying the claim type, the system determines which documents are required.

Required documents are checked against the documents uploaded by the customer.

The system must not assume that a missing document exists.

### All Required Documents Present

```text
Required Documents Check
        ↓
All documents present
        ↓
Continue processing
```

### Documents Missing

If one or more required documents are missing:

```text
Required Documents Check
        ↓
Documents missing
        ↓
Identify missing documents
        ↓
Request missing documents
        ↓
Customer uploads documents
        ↓
Run required-document check again
```

The system lists exactly which documents are missing.

The claim is not approved or rejected because of missing documents.

The claim enters:

```text
WAITING_FOR_DOCUMENTS
```

The customer can upload the missing documents and continue the claim.

---

## 8. Policy Lookup and Validation

Once the required documents are available, the backend validates the selected policy.

The system checks:

- Policy exists
- Policy status
- Policy start date
- Policy end date
- Claim incident date
- Remaining policy limit
- Applicable riders

The system must use the actual selected policy.

It must not search for or substitute another policy.

---

## 9. Policy Validity

The system determines whether the policy is valid for the claim.

```text
Policy Validation
        ↓
Is policy valid?
```

If the policy is invalid:

```text
Invalid Policy
        ↓
REJECT
```

If the policy is valid:

```text
Valid Policy
        ↓
Continue to coverage evaluation
```

---

## 10. Universal Exclusions

Universal exclusions are checked before normal coverage approval.

These exclusions apply across all insurance product lines.

The system checks for:

- War and terrorism
- Nuclear and radioactive events
- Intentional acts
- Illegal activity
- Sanctions
- Consequential loss

If a universal exclusion applies:

```text
Universal Exclusion
        ↓
REJECT
        ↓
Generate customer message
```

The universal exclusion overrides other coverage.

---

## 11. Handbook Retrieval

If no universal exclusion applies, the system retrieves the relevant rules from the insurance policy handbook.

The handbook is used through the RAG pipeline.

```text
Claim information
        +
Policy information
        +
Claim type
        ↓
Handbook Retrieval / RAG
        ↓
Relevant clauses
```

The system grounds the coverage decision in the retrieved handbook clauses.

The system must not make coverage decisions based on unsupported assumptions.

---

## 12. Coverage Validation

The retrieved handbook rules are evaluated against the claim.

The system checks:

- Whether the peril is covered
- Whether the claim type is covered
- Applicable exclusions
- Applicable waiting periods
- Applicable sub-limits
- Applicable riders
- Required evidence
- Policy conditions

The system determines:

```text
Covered?
```

### Not Covered

```text
Not Covered
    ↓
REJECT
    ↓
Generate customer message
```

### Covered

```text
Covered
    ↓
Continue
```

---

## 13. Supporting Evidence Check

The system verifies whether the available claim evidence supports the coverage decision.

This includes the uploaded documents and extracted claim information.

If the evidence is insufficient:

```text
Insufficient Supporting Evidence
        ↓
ROUTE_TO_HUMAN
```

The system must not invent missing information.

---

## 14. Rider Validation

If the claim depends on a rider, the system checks whether the required rider exists on the selected policy and applies to the claim.

Examples include:

- Flood rider
- Adventure rider
- All-Risks / portable items rider

The rider must be valid for the relevant claim.

If the required rider is absent:

```text
Required Rider Missing
        ↓
REJECT
```

If the rider is present and valid:

```text
Valid Rider
        ↓
Continue
```

---

## 15. Remaining Limit Check

The system checks the policy's remaining limit.

```text
Claim Amount
        ↓
Remaining Policy Limit
```

If the remaining limit is insufficient:

```text
Insufficient Remaining Limit
        ↓
ROUTE_TO_HUMAN
```

The system must not approve an amount that exceeds the available policy limit.

---

## 16. Deductible Calculation

If the claim is covered, the system calculates the applicable deductible.

```text
Covered Claim
        ↓
Deductible Calculation
        ↓
Potential Settlement Amount
```

If the payable amount is below the applicable deductible:

```text
Below Deductible
        ↓
BELOW_DEDUCTIBLE
```

---

## 17. Duplicate Detection

The system checks whether the claim may duplicate an existing claim.

The check can use claim information such as:

- Policy
- Claim type
- Incident date
- Claimed amount
- Extracted claim information
- Uploaded documents

If a duplicate is detected:

```text
Duplicate Detected
        ↓
ROUTE_TO_HUMAN
```

---

## 18. Fraud and Risk Detection

The system evaluates the claim for fraud or risk signals.

Examples include:

- Suspicious claim patterns
- Unsupported monetary amounts
- Missing supporting evidence
- Potential duplicate claims
- Other risk signals detected by the system

If a risk signal is detected:

```text
Risk Detected
        ↓
ROUTE_TO_HUMAN
```

A risk signal prevents automatic settlement.

---

## 19. Auto-Approval Conditions

A claim can only be automatically approved when all required conditions pass.

The auto-approval decision checks:

```text
Policy valid
        AND
Required documents present
        AND
No universal exclusion
        AND
Coverage confirmed
        AND
Supporting evidence sufficient
        AND
Required rider valid
        AND
Remaining limit sufficient
        AND
No duplicate detected
        AND
No fraud/risk signal
        AND
Claim amount ≤ EGP 10,000
```

If all conditions pass:

```text
AUTO_APPROVE
```

---

## 20. Decision Engine

The decision engine produces one of the workflow outcomes.

Possible outcomes:

```text
AUTO_APPROVE
REJECT
ROUTE_TO_HUMAN
ESCALATE
BELOW_DEDUCTIBLE
```

### AUTO_APPROVE

The claim passes all automatic checks and is within the EGP 10,000 auto-approval limit.

### REJECT

The claim is not covered, violates an exclusion, fails policy conditions, or otherwise cannot be paid.

### ROUTE_TO_HUMAN

The claim requires assessor review.

Examples:

- Risk detected
- Duplicate detected
- Insufficient evidence
- Remaining limit issue
- Complex claim
- Automatic processing cannot safely determine the result

### ESCALATE

The claim requires escalation because the system identifies an issue that needs additional human handling.

### BELOW_DEDUCTIBLE

The covered claim amount does not exceed the applicable deductible.

---

## 21. Human Review

Claims routed for human review enter the Human Review queue.

Human Review is a workflow state.

The Assessor is the user role responsible for reviewing routed claims.

The assessor can view the information required to make the decision.

This includes:

- Claim information
- Uploaded documents
- Extracted information
- Policy information
- Relevant handbook evidence
- AI recommendation
- Risk signals
- Previous processing information

The assessor can choose:

```text
Approve
Reject
Route / Escalate
Override AI Recommendation
```

---

## 22. Assessor Decision

The assessor reviews the claim and makes the final decision.

```text
Human Review
      ↓
Assessor Decision
      ├── Approve
      ├── Reject
      ├── Route / Escalate
      └── Override AI Recommendation
```

The assessor's decision is recorded.

The system records the reviewer and review information for audit purposes.

---

## 23. Final Decision

After automatic processing or human review, the system stores the final claim decision.

```text
Claim Processing
      ↓
Final Decision
```

The final decision is associated with the claim.

The decision includes the reasoning and relevant handbook clause when applicable.

Risk information is also recorded when detected.

---

## 24. Customer Message

After the final decision, the system generates a customer-facing message.

The message explains the claim outcome.

Examples:

```text
Approved
Rejected
Below Deductible
Routed / Escalated
```

The system displays the generated customer message.

The message is a draft generated by the system.

It is not automatically sent to the customer as part of this workflow.

---

## 25. Audit Trail

Important claim-processing events are recorded in the audit trail.

Examples include:

- Claim creation
- Document upload
- Missing-document request
- Policy validation
- Coverage decision
- Risk detection
- Human review
- Assessor decision
- Final decision

The audit trail supports traceability of the claim lifecycle.

---

## 26. Complete Workflow

The complete workflow can be represented as:

```text
Customer Login
      ↓
Load Customer Policies
      ↓
Select Owned Policy
      ↓
Policy Ownership Validation
      │
      ├── Invalid
      │     ↓
      │   Show Error
      │
      └── Valid
            ↓
       Create Claim
            ↓
       Upload Documents
            ↓
       OCR / Vision
            ↓
       Claim Extraction
            ↓
       Claim Type Identification
            ↓
       Required Documents Check
            │
            ├── Missing
            │     ↓
            │   Request Documents
            │     ↓
            │   Customer Uploads
            │     ↓
            │   Required Documents Check
            │
            └── Complete
                  ↓
             Policy Lookup
                  ↓
             Policy Validation
                  │
                  ├── Invalid → REJECT
                  │
                  └── Valid
                       ↓
                Universal Exclusions
                       │
                       ├── Excluded → REJECT
                       │
                       └── Not Excluded
                              ↓
                       Handbook RAG
                              ↓
                       Coverage Validation
                              │
                              ├── Not Covered → REJECT
                              │
                              └── Covered
                                   ↓
                          Supporting Evidence
                                   │
                                   ├── Insufficient
                                   │       ↓
                                   │   ROUTE_TO_HUMAN
                                   │
                                   └── Sufficient
                                          ↓
                                    Rider Validation
                                          ↓
                                    Remaining Limit
                                          ↓
                                    Deductible Check
                                          ↓
                                    Duplicate Detection
                                          ↓
                                    Fraud / Risk Detection
                                          │
                                          ├── Risk Detected
                                          │       ↓
                                          │   ROUTE_TO_HUMAN
                                          │
                                          └── No Risk
                                                 ↓
                                      Auto-Approval Check
                                                 │
                                                 ├── Amount > EGP 10,000
                                                 │       ↓
                                                 │   ROUTE_TO_HUMAN
                                                 │
                                                 └── All Conditions Pass
                                                         ↓
                                                    AUTO_APPROVE

ROUTE_TO_HUMAN
      ↓
Human Review Queue
      ↓
Assessor Review
      ↓
Approve / Reject / Route / Override
      ↓
Final Decision
      ↓
Generate Customer Message
      ↓
Display Customer Message
      ↓
Audit Log
```

---

## 27. Core Workflow Principle

The system follows this order:

```text
Documents
    ↓
Claim Understanding
    ↓
Required Documents
    ↓
Policy Validation
    ↓
Exclusions
    ↓
Handbook Evidence
    ↓
Coverage
    ↓
Financial Checks
    ↓
Risk Checks
    ↓
Decision
    ↓
Human Review when required
    ↓
Final Decision
    ↓
Customer Message
```

Every automatic decision must be based on the claim data, the selected policy, the uploaded evidence, and the relevant handbook rules.
