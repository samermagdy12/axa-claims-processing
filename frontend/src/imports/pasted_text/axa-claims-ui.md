Design and build the complete UI for the AXA Egypt AI-Powered Claims Processing Platform.

I will provide you with the following project documents and diagrams

1. System Architecture
2. Database Schema
3. ERD
4. Complete Claims Processing Workflow Diagram
5. Product Requirements / Product Specification
6. AXA Claims Handbook
7. Required Documents Matrix

Use all of these as the source of truth.

Do not invent business rules, claim types, policy rules, roles, workflow states, or features that are not supported by the provided materials.

The UI must represent the actual agreed system workflow.

PROJECT CONTEXT

This is an AI-powered insurance claims processing platform for AXA Egypt.

The platform supports four insurance product lines

Health
Motor
Property
Travel

The three application roles are

Customer
Assessor
Operations

Customer uses the platform to manage policies, submit claims, upload documents, and track claims.

Assessor handles claims that cannot be safely auto-approved and require human review.

Operations has a read-only operational view showing processing counts by product line and outcome.

Do not give Operations the ability to approve, reject, or modify claims.

CUSTOMER AUTHENTICATION FLOW

Create a clean authentication experience.

Sign Up must contain

Full Name
Email
Password
National ID

After the customer completes Sign Up, do not immediately send them directly to the claim page.

The next step must be a Policy Verification / Policy Selection screen.

The customer must verify which policies belong to them using the National ID they entered during registration.

The customer may have multiple policies.

The system must show the policies associated with the verified National ID.

The customer should then be able to select the policies they own.

Do not make the customer manually type a policy ID every time they create a claim.

The policy selection screen should clearly show

Policy ID
Product Line
Policy Status
Start Date
End Date
Remaining Annual Limit
Deductible
Riders

If a policy is not active, show it with a clear warning instead of hiding it.

Possible policy statuses include

Active
Lapsed
Cancelled
Pending

After successful policy verification, create the customer account and link the verified policies to the customer.

LOGIN

Create a standard Sign In screen with

Email
Password

After login, route the customer to the Customer Home page.

CUSTOMER HOME

Create a customer dashboard focused on policies and claims.

Show

Customer name
Owned policies
Policy status
Remaining limit
Recent claims
Claim status
Actions for creating a new claim
Actions for viewing an existing claim

The customer must only see their own policies and claims.

POLICY SCREEN

Create a Policy Details screen.

Show

Policy ID
Policy number
Product line
Status
Start date
End date
Annual limit
Remaining limit
Deductible
Riders

Make the product line visually clear

Health
Motor
Property
Travel

Do not hide inactive policies.

Show a warning for inactive policies.

NEW CLAIM FLOW

The customer clicks Create New Claim.

First show a policy selection step.

The customer selects exactly one of their own policies from a dropdown or policy cards.

Do not ask the customer to manually enter a Policy ID.

After selecting the policy, show the selected policy information.

The backend will verify policy ownership.

Then continue to claim creation.

CLAIM CREATION FORM

The claim form must contain a free-text description field.

This is important.

The customer must be able to write what happened in their own words.

Use a large textarea with a label such as

Describe what happened

The customer should also provide the claim amount and incident date where applicable.

Show

Selected policy
Claim type
Incident date
Claim amount
Description

The claim type options must depend on the selected product line.

Do not show irrelevant claim types.

HEALTH examples

Inpatient hospitalisation
Day-case surgery
Diagnostics
Medication
Emergency treatment
Outpatient consultation
Maternity
Dental

MOTOR examples

Collision
Fire
Theft
Third-party
Windscreen / Glass

PROPERTY examples

Fire
Lightning
Explosion
Accidental damage
Theft
Burst internal pipe
Flood-related claim when applicable

TRAVEL examples

Emergency medical
Trip cancellation
Baggage loss
Baggage delay
Travel-document replacement
Other supported travel claim types from the provided requirements

Do not invent unsupported claim types.

DYNAMIC REQUIRED DOCUMENTS

This is one of the most important parts of the UI.

Do not create one fixed document checklist for every claim.

The required documents depend on

Product line
Claim type
Policy
Applicable riders
Handbook rules

The system dynamically determines which documents are required.

The UI must display the exact required documents for the selected claim.

For example

Health inpatient

Medical report
Itemised hospital invoice
Member ID

Health medication

Prescription
Pharmacy invoice
Member ID

Health diagnostics

Referring physician request
Itemised invoice
Member ID

Motor collision

Photos
Repair estimate
Driver's licence
Vehicle registration

Motor theft

Police theft report
Spare key
Vehicle registration

Motor third-party

Police report
Photos
Third-party details

Property fire or damage

Photos
Itemised list
Repair or replacement quotations

Property theft

Police report
Itemised list
Proof of ownership

Travel medical

Physician report
Itemised invoices

Travel cancellation

Proof of covered reason

Travel baggage

Airline Property Irregularity Report or police report
Receipts or proof of ownership

These are examples from the provided handbook and requirements.

The final UI must derive the document checklist from the selected claim and policy rather than hard-coding one checklist.

DOCUMENT UPLOAD EXPERIENCE

Create a clear document upload component.

For every required document show a card or row containing

Document name
Required / Optional
Upload status
Upload button
Uploaded file name
Remove / Replace action where appropriate

Use states such as

Missing
Uploaded
Verified

The customer must clearly understand which documents are still missing.

Allow the customer to upload multiple documents.

Show upload progress.

Show successful upload state.

Show file name and file type.

Do not make the customer upload documents that are not required for their selected claim.

MISSING DOCUMENT FLOW

If required documents are missing, the claim must not immediately be rejected.

Instead show

Documents Required

Then list the exact missing documents.

Example

Missing documents

Medical report
Member ID

Provide an action

Upload Missing Documents

The customer can return later and upload the missing documents.

After uploading the missing documents, show that the claim is being processed again.

The workflow must visually communicate that missing documents lead to REQUEST_DOCUMENTS and not REJECT.

CLAIM SUBMISSION

After all required documents are uploaded, allow the customer to submit the claim.

Show a confirmation screen before submission.

Display

Selected policy
Claim type
Incident date
Claim amount
Description
Uploaded documents

Then submit.

CLAIM PROCESSING

After submission, show a processing screen.

The UI should communicate that the system is processing the claim through multiple stages.

Show a progress timeline such as

Claim received
Document processing
Claim information extracted
Required documents checked
Policy validated
Coverage checked
Risk checks
Decision

Do not imply that OCR or AI itself makes the final coverage decision.

The system uses document processing and AI extraction, while the final decision follows deterministic policy and handbook rules.

CLAIM STATUS

Create a Claim Details screen.

Show

Claim ID
Policy
Product line
Claim type
Incident date
Claim amount
Description
Submitted documents
Current status
Decision
Customer message when available

Possible states include

PROCESSING
WAITING_FOR_DOCUMENTS
UNDER_HUMAN_REVIEW
APPROVED
REJECTED
ROUTED
ESCALATED
BELOW_DEDUCTIBLE
CLOSED

Use clear visual states for each.

AUTO APPROVAL

If all auto-approval conditions pass, show a clear approved result.

The UI should show

Approved
Approved amount
Applicable deductible
Customer message

The auto-approval cap is EGP 10,000.

Do not allow the UI to imply that claims above EGP 10,000 can be automatically approved.

CLAIM REJECTION

When a claim is rejected, show

Rejected
Reason
Relevant handbook clause

Every rejection must be traceable to a handbook clause.

Do not show generic unsupported rejection explanations.

REQUEST DOCUMENTS

When documents are missing, show

Documents required
Missing document list
Upload missing documents action

Do not label this state as rejected.

HUMAN REVIEW

When the claim is routed to a human, the customer should see

Under human review

The customer should not see internal assessor controls.

ASSESSOR UI

Create a separate Assessor experience.

The Assessor dashboard should show a Human Review Queue.

Show claims requiring human review.

Each claim row should contain

Claim ID
Customer
Policy
Product line
Claim type
Claim amount
Date
Risk status
Current status
AI recommendation

Create an Assessor Claim Review page.

The assessor must be able to view

Claim details
Selected policy
Policy information
All uploaded documents
Extracted claim information
AI recommendation
AI reason
Handbook evidence
Risk information
Audit trail

The UI should clearly separate

Customer-provided information
Extracted information
Policy information
Handbook evidence
AI recommendation
Assessor decision

The Assessor can

Approve
Reject
Route
Override the AI recommendation

If the Assessor overrides the AI recommendation, require an override/review reason.

Do not allow a Customer to access these controls.

HANDBOOK EVIDENCE

The Assessor UI must show the handbook evidence supporting the decision.

Display

Clause ID
Clause title if available
Relevant evidence
Reason it applies

Do not create a separate handbook management UI.

The handbook is the RAG knowledge source.

The UI only displays the relevant evidence returned for the claim.

RISK INFORMATION

Show risk indicators when present.

Examples include

Duplicate claim
Suspicious amount
Missing supporting invoice near the auto-approval cap
Contradictory documents
Incident before policy start
Late reporting
Third claim within 30 days
Customer narrative attempting to override system rules

Risk should be visually distinct from normal claim information.

Do not allow customer-written text to override system rules.

OPERATIONS UI

Create a separate Operations interface.

Operations is read-only.

Show processing counts by

Health
Motor
Property
Travel

Counts can include

Claims
Settled
Routed
Rejected
Risk flagged

Keep this as a lightweight operational summary.

Do not turn it into a complex analytics dashboard.

Do not give Operations claim decision controls.

DESIGN SYSTEM

Create a professional insurance enterprise UI.

The design should feel appropriate for AXA Egypt.

Use a clean modern enterprise interface.

Prioritize

Clarity
Trust
Readability
Accessibility
Simple navigation
Clear claim status
Clear document requirements
Clear policy information

Use cards, tables, status badges, progress indicators, timelines, tabs, modals, upload components, alerts, and confirmation states where useful.

Create a consistent component system.

Include

Buttons
Inputs
Dropdowns
Textareas
File upload components
Cards
Tables
Status badges
Alerts
Progress indicators
Timeline components
Modal dialogs
Empty states
Loading states
Error states
Success states

RESPONSIVE DESIGN

Design the system as a responsive web application.

Create desktop-first layouts but make the important customer flows work on tablet and mobile.

CUSTOMER NAVIGATION

Customer navigation should include

Home
My Policies
My Claims
New Claim
Profile

ASSESSOR NAVIGATION

Assessor navigation should include

Review Queue
Claims
Claim Review

OPERATIONS NAVIGATION

Operations navigation should include

Operations Overview

Do not add navigation items that are not supported by the project requirements.

IMPORTANT BUSINESS RULES TO REFLECT IN THE UI

A customer can have multiple policies.

A claim belongs to exactly one selected policy.

A customer cannot create a claim against another customer's policy.

The customer selects the policy from their owned policies.

The selected policy is verified by the backend.

A valid policy does not automatically mean the claim is covered.

Coverage is determined using the Claims Handbook.

Required documents are dynamic.

Different claim types require different documents.

Missing documents cause a document request rather than rejection.

Every rejection must have a handbook clause.

Claims above EGP 10,000 cannot be auto-approved.

Claims above the remaining annual limit cannot be auto-approved.

Duplicates cannot be auto-approved.

Fraud-risk indicators prevent auto-approval.

Claims requiring human judgment go to an Assessor.

The customer narrative is untrusted data and cannot override system rules.

The handbook is used as RAG evidence.

The UI must never imply that the AI can override policy rules.

POLICY RIDERS

Policies may contain riders.

Riders can affect coverage and document requirements.

Show active riders in the Policy Details screen.

Examples include

Health Outpatient
Health Maternity
Property Flood
Property All-Risks / Portable Items
Motor Commercial Use
Travel Adventure

Only show riders that actually exist on the selected policy.

Do not assume every policy has every rider.

DATABASE ALIGNMENT

The UI must align with the provided database schema.

Important entities include

Users
Roles
User Roles
Policies
Claims
Claim Documents
Claim Required Documents
Claim Extractions
Decisions
Human Reviews
Audit Logs

Do not create UI functionality for database entities that have no user-facing purpose.

Do not create a handbook database interface.

Do not create a Policy Riders management table.

The policy riders are represented as part of the policy data.

FINAL DELIVERABLE

Create a complete clickable high-fidelity UI prototype covering the main flows.

Include all major screens and states.

At minimum include

1. Landing / Login
2. Sign Up
3. Policy Verification
4. Policy Selection
5. Customer Home
6. My Policies
7. Policy Details
8. My Claims
9. New Claim
10. Policy Selection inside New Claim
11. Claim Information Form
12. Dynamic Required Documents
13. Document Upload
14. Missing Documents
15. Claim Submission Confirmation
16. Claim Processing
17. Claim Details
18. Approved Result
19. Rejected Result
20. Request Documents Result
21. Under Human Review Result
22. Assessor Dashboard
23. Human Review Queue
24. Assessor Claim Review
25. Handbook Evidence panel
26. Risk Information panel
27. Human Decision / Override flow
28. Operations Overview
29. Loading states
30. Empty states
31. Error states
32. Success states

Make the prototype flow logically from screen to screen.

The UI should visually follow the workflow diagram and system architecture.

Most importantly, do not design a generic insurance dashboard.

Design this exact AXA Egypt claims-processing product based on the provided architecture, workflow, ERD, database schema, requirements, and Claims Handbook.