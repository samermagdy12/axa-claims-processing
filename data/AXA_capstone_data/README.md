# AXA Claims Capstone — Data

Everything the agent reads. No database — plain files you can open and explain.

## `policy_handbook/`  — the RAG corpus ("Know")
~40 clauses across 7 files (general rules, health, motor, property, travel, universal
exclusions, documents matrix). Too large to paste into a prompt on purpose: you must
retrieve. Contains deliberate distractors — burst pipe (covered) vs flood (excluded),
basic vs cosmetic dental, baggage delay vs loss, third-party vs comprehensive — so
top-1 retrieval is not automatically right. Every coverage decision must cite a clause.

## `policies.json`  — the lookup table ("Act")
150 policy records. `lookup_policy(policy_id)` reads from here (same in-memory-dict
pattern as the Week 2 banking task). Fields: policy_id, holder_name, national_id, line,
status (active/lapsed/pending/cancelled), start/end dates, annual_limit, remaining_limit,
deductible, riders, and (motor) cover type. 15 policies are referenced by the sample
claims with fixed states; the rest are realistic filler.

## `claims/`  — the inputs
27 claims as plain text (id, policy id, date, narrative). Feed these to the agent. They
seed your Milestone-5 eval set.


## `sample_documents/`  — the OCR intake
The 27 claims, rendered as photo-like claim-submission documents (JPEG). These are what a
customer actually uploads. Your intake runs OCR / a vision model over one of these to pull
out the claim text and key fields, then hands that to the decision engine. They're rendered
from the text in `claims/`, so each `claims/CLM-XXX.txt` doubles as the reference for what a
good extraction should recover from `sample_documents/CLM-XXX.jpg`.

## `answer_key.json`  — ground truth (instructor copy)
For each claim: the correct outcome, the tools a correct agent should fire, and the
handbook clause that justifies it. Outcomes: AUTO_APPROVE, ROUTE_TO_HUMAN,
REQUEST_DOCUMENTS, REJECT, ESCALATE.

The auto-approval cap is **EGP 10,000** (handbook Clause 0.2). The data is seeded so all
five decision paths — plus a duplicate and a prompt-injection override attempt — actually
occur.
