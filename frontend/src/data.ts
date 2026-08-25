import type { Policy, Claim, AssessorClaim } from './types';

export const CUSTOMER_POLICIES: Policy[] = [
  {
    id: 'pol-h-2023-001',
    number: 'POL-H-2023-001',
    productLine: 'HEALTH',
    status: 'ACTIVE',
    startDate: '2023-01-15',
    endDate: '2025-01-14',
    annualLimit: 50000,
    remainingLimit: 38500,
    deductible: 500,
    riders: ['OUTPATIENT', 'MATERNITY'],
  },
  {
    id: 'pol-m-2022-007',
    number: 'POL-M-2022-007',
    productLine: 'MOTOR',
    status: 'ACTIVE',
    startDate: '2022-06-01',
    endDate: '2025-05-31',
    annualLimit: 80000,
    remainingLimit: 80000,
    deductible: 1000,
    riders: [],
  },
  {
    id: 'pol-p-2024-003',
    number: 'POL-P-2024-003',
    productLine: 'PROPERTY',
    status: 'LAPSED',
    startDate: '2023-03-10',
    endDate: '2024-03-09',
    annualLimit: 120000,
    remainingLimit: 0,
    deductible: 2000,
    riders: ['FLOOD'],
  },
  {
    id: 'pol-t-2024-011',
    number: 'POL-T-2024-011',
    productLine: 'TRAVEL',
    status: 'ACTIVE',
    startDate: '2024-01-01',
    endDate: '2025-12-31',
    annualLimit: 25000,
    remainingLimit: 25000,
    deductible: 0,
    riders: ['ADVENTURE'],
  },
];

export const CUSTOMER_CLAIMS: Claim[] = [
  {
    id: 'clm-001',
    policyId: 'pol-h-2023-001',
    policyNumber: 'POL-H-2023-001',
    productLine: 'HEALTH',
    claimType: 'Inpatient Hospitalisation',
    incidentDate: '2024-01-10',
    submissionDate: '2024-01-15',
    claimedAmount: 8500,
    description:
      'Admitted to Cairo Medical Center for acute appendicitis. Emergency surgery performed. 3 nights hospitalization. All procedures medically necessary.',
    status: 'APPROVED',
    decision: {
      outcome: 'AUTO_APPROVE',
      approvedAmount: 8000,
      deductible: 500,
      reason: 'All auto-approval conditions satisfied per Clause 0.2.',
      handbookClause: 'Clause 0.2, Clause 1.1',
      customerMessage:
        'Your claim has been approved. The approved amount is EGP 8,000 (EGP 8,500 less EGP 500 deductible). This will be reflected in your account.',
    },
    documents: [
      { type: 'Medical Report', fileName: 'medical_report_cairo_medical.pdf', status: 'VERIFIED' },
      { type: 'Itemised Hospital Invoice', fileName: 'hospital_invoice_jan2024.pdf', status: 'VERIFIED' },
      { type: 'Member ID', fileName: 'member_card_front.jpg', status: 'VERIFIED' },
    ],
  },
  {
    id: 'clm-002',
    policyId: 'pol-m-2022-007',
    policyNumber: 'POL-M-2022-007',
    productLine: 'MOTOR',
    claimType: 'Collision',
    incidentDate: '2024-02-20',
    submissionDate: '2024-02-21',
    claimedAmount: 15000,
    description:
      'Vehicle collision at Ring Road intersection near Maadi exit. Front bumper and hood damage. Other party was at fault. No police report taken at scene.',
    status: 'WAITING_FOR_DOCUMENTS',
    decision: {
      outcome: 'REQUEST_DOCUMENTS',
      reason: 'Required documents missing.',
      missingDocuments: ["Driver's Licence", 'Repair Estimate'],
      customerMessage:
        "Your claim is on hold. Please upload the missing documents to continue processing. Your Driver's Licence and a Repair Estimate from a certified garage are required.",
    },
    documents: [
      { type: 'Photos of Damage', fileName: 'damage_photos_ring_road.zip', status: 'UPLOADED' },
      { type: 'Vehicle Registration', fileName: 'vehicle_reg_2022.pdf', status: 'UPLOADED' },
      { type: "Driver's Licence", status: 'MISSING' },
      { type: 'Repair Estimate', status: 'MISSING' },
    ],
  },
  {
    id: 'clm-003',
    policyId: 'pol-h-2023-001',
    policyNumber: 'POL-H-2023-001',
    productLine: 'HEALTH',
    claimType: 'Medication',
    incidentDate: '2024-02-25',
    submissionDate: '2024-02-26',
    claimedAmount: 1200,
    description:
      'Monthly medication for cardiovascular condition as prescribed by cardiologist Dr. Hossam Kamal at Ain Shams University Hospital.',
    status: 'PROCESSING',
    documents: [
      { type: 'Prescription', fileName: 'prescription_feb2024.pdf', status: 'UPLOADED' },
      { type: 'Pharmacy Invoice', fileName: 'pharmacy_invoice_feb2024.pdf', status: 'UPLOADED' },
      { type: 'Member ID', fileName: 'member_card.jpg', status: 'UPLOADED' },
    ],
  },
  {
    id: 'clm-004',
    policyId: 'pol-h-2023-001',
    policyNumber: 'POL-H-2023-001',
    productLine: 'HEALTH',
    claimType: 'Outpatient Consultation',
    incidentDate: '2024-01-05',
    submissionDate: '2024-01-08',
    claimedAmount: 350,
    description:
      'GP consultation at private clinic for seasonal respiratory infection. Prescribed antibiotics and rest.',
    status: 'REJECTED',
    decision: {
      outcome: 'REJECT',
      reason:
        'Outpatient consultation is not covered without the Outpatient rider. Policy POL-H-2023-001 does not carry this rider at the time of the incident.',
      handbookClause: 'Clause 1.2',
      customerMessage:
        'Your claim for outpatient consultation has been rejected. Outpatient consultations are only covered when your policy carries the Outpatient rider (Clause 1.2). Your current policy does not include this rider. Please contact AXA Egypt to add the Outpatient rider to your policy for future cover.',
    },
    documents: [
      { type: 'Medical Report', fileName: 'gp_report_jan2024.pdf', status: 'VERIFIED' },
      { type: 'Member ID', fileName: 'member_card.jpg', status: 'VERIFIED' },
    ],
  },
  {
    id: 'clm-005',
    policyId: 'pol-m-2022-007',
    policyNumber: 'POL-M-2022-007',
    productLine: 'MOTOR',
    claimType: 'Windscreen / Glass',
    incidentDate: '2024-02-10',
    submissionDate: '2024-02-11',
    claimedAmount: 850,
    description:
      'Windscreen cracked by a stone chip on the highway. Single crack across the driver\'s field of vision requiring full replacement.',
    status: 'BELOW_DEDUCTIBLE',
    decision: {
      outcome: 'BELOW_DEDUCTIBLE',
      reason:
        'Claim amount EGP 850 is at or below the policy deductible of EGP 1,000. No payout is due. The claim is covered, but the deductible absorbs the full amount.',
      handbookClause: 'Clause 0.4, Clause 2.7',
      customerMessage:
        'Your windscreen claim is covered under Clause 2.7, however the claimed amount of EGP 850 is below your policy deductible of EGP 1,000 (Clause 0.4). No payment is due, but this claim does not affect your no-claims record.',
    },
    documents: [
      { type: 'Photos of Damage', fileName: 'windscreen_crack.jpg', status: 'VERIFIED' },
      { type: 'Repair Estimate', fileName: 'glass_repair_quote.pdf', status: 'VERIFIED' },
      { type: 'Vehicle Registration', fileName: 'vehicle_reg_2022.pdf', status: 'VERIFIED' },
    ],
  },
  {
    id: 'clm-006',
    policyId: 'pol-t-2024-011',
    policyNumber: 'POL-T-2024-011',
    productLine: 'TRAVEL',
    claimType: 'Baggage Loss',
    incidentDate: '2024-03-05',
    submissionDate: '2024-03-07',
    claimedAmount: 4200,
    description:
      'Luggage permanently lost on return flight from Dubai (Emirates EK-928). Filed property irregularity report with airline. Bag contained clothing, electronics, and personal items.',
    status: 'UNDER_HUMAN_REVIEW',
    decision: {
      outcome: 'ROUTE_TO_HUMAN',
      reason: 'Claim amount within auto-approval cap, all documents present, no risk indicators. Coverage validated. Routed for standard assessor approval.',
      customerMessage: 'Your baggage loss claim is under review by an AXA assessor. All your documents have been received and verified.',
    },
    documents: [
      { type: 'Airline PIR or Police Report', fileName: 'emirates_pir_ek928.pdf', status: 'VERIFIED' },
      { type: 'Receipts / Proof of Ownership', fileName: 'purchase_receipts.pdf', status: 'VERIFIED' },
    ],
  },
];

export const ASSESSOR_CLAIMS: AssessorClaim[] = [
  {
    id: 'clm-004',
    customerName: 'Layla Mostafa',
    policyNumber: 'POL-H-2022-089',
    productLine: 'HEALTH',
    claimType: 'Inpatient Hospitalisation',
    claimedAmount: 23500,
    incidentDate: '2024-02-15',
    submittedDate: '2024-02-16',
    status: 'UNDER_HUMAN_REVIEW',
    riskStatus: 'HIGH',
    aiRecommendation: 'ROUTE_TO_HUMAN',
    aiReason:
      'Claim amount EGP 23,500 exceeds the auto-approval cap of EGP 10,000 (Clause 0.2f). Human assessor approval required.',
    description:
      'Patient admitted to As-Salam International Hospital on 15/02/2024 for acute myocardial infarction. 12 nights in cardiac care unit. Emergency angioplasty performed.',
    riskIndicators: ['Claim amount EGP 23,500 exceeds EGP 10,000 auto-approval cap (Clause 0.2f)'],
    handbookEvidence: [
      {
        clauseId: 'Clause 0.2(f)',
        title: 'Auto-approval cap',
        evidence:
          'Auto-approval requires claim amount at or below EGP 10,000. This claim is EGP 23,500 — exceeds cap by EGP 13,500.',
        reason: 'Cap exceeded — human review required',
      },
      {
        clauseId: 'Clause 1.1',
        title: 'Inpatient hospitalisation cover',
        evidence:
          'Inpatient hospitalisation is a covered peril under the Health policy. Emergency cardiac treatment is included.',
        reason: 'Coverage confirmed subject to limits',
      },
      {
        clauseId: 'Clause 1.8',
        title: 'Room and board sub-limit',
        evidence:
          'Room and board sub-limit is EGP 1,500 per night. 12 nights × EGP 1,500 = EGP 18,000 sub-limit applies.',
        reason: 'Sub-limit to be applied on approved amount',
      },
    ],
    extractedData: {
      claimType: 'Inpatient Hospitalisation',
      incidentDate: '2024-02-15',
      amount: 23500,
      hospital: 'As-Salam International Hospital, Cairo',
      daysHospitalized: 12,
      diagnosis: 'Acute myocardial infarction (I21.9)',
      procedure: 'Emergency percutaneous coronary intervention',
      confidence: 0.97,
    },
    policyInfo: {
      number: 'POL-H-2022-089',
      productLine: 'HEALTH',
      status: 'ACTIVE',
      annualLimit: 100000,
      remainingLimit: 76500,
      deductible: 500,
      riders: ['OUTPATIENT'],
    },
    documents: [
      { type: 'Medical Report', fileName: 'medical_report_dr_samy.pdf', status: 'VERIFIED' },
      { type: 'Itemised Hospital Invoice', fileName: 'as_salam_invoice_23500.pdf', status: 'VERIFIED' },
      { type: 'Member ID', fileName: 'member_card_layla.jpg', status: 'VERIFIED' },
    ],
    auditTrail: [
      { action: 'CLAIM_CREATED', timestamp: '2024-02-16 09:15', actor: 'Customer', details: 'Claim submitted by Layla Mostafa' },
      { action: 'DOCUMENT_UPLOADED', timestamp: '2024-02-16 09:18', actor: 'Customer', details: '3 documents uploaded successfully' },
      { action: 'OCR_COMPLETED', timestamp: '2024-02-16 09:22', actor: 'System', details: 'OCR extraction completed. Confidence: 97%' },
      { action: 'CLAIM_EXTRACTED', timestamp: '2024-02-16 09:22', actor: 'System', details: 'Structured data extracted from medical report and invoice' },
      { action: 'REQUIRED_DOCUMENTS_CHECK', timestamp: '2024-02-16 09:22', actor: 'System', details: 'All required documents present and verified' },
      { action: 'POLICY_VALIDATED', timestamp: '2024-02-16 09:23', actor: 'System', details: 'Policy ACTIVE. Incident date within policy period. No waiting period issue.' },
      { action: 'HANDBOOK_RETRIEVED', timestamp: '2024-02-16 09:23', actor: 'System', details: 'Handbook RAG retrieved Clauses 0.2, 1.1, 1.8' },
      { action: 'COVERAGE_CHECKED', timestamp: '2024-02-16 09:23', actor: 'System', details: 'Covered under Clause 1.1. Sub-limits apply per Clause 1.8.' },
      { action: 'RISK_CHECKED', timestamp: '2024-02-16 09:23', actor: 'System', details: 'Amount EGP 23,500 exceeds EGP 10,000 auto-approval cap (Clause 0.2f). No other risk indicators.' },
      { action: 'DECISION_MADE', timestamp: '2024-02-16 09:23', actor: 'System', details: 'ROUTE_TO_HUMAN — cap exceeded. Claim queued for assessor review.' },
    ],
  },
  {
    id: 'clm-005',
    customerName: 'Omar Farouk',
    policyNumber: 'POL-M-2023-045',
    productLine: 'MOTOR',
    claimType: 'Theft',
    claimedAmount: 45000,
    incidentDate: '2024-02-18',
    submittedDate: '2024-02-19',
    status: 'UNDER_HUMAN_REVIEW',
    riskStatus: 'HIGH',
    description:
      'Vehicle stolen from residential parking at Heliopolis address on the night of 18/02/2024. Police report filed. Spare key provided.',
    aiRecommendation: 'ESCALATE',
    aiReason:
      'Fraud-risk indicator: this is the third claim on policy POL-M-2023-045 within 30 days (Clause 0.6e). Additionally, claim amount EGP 45,000 exceeds auto-approval cap. Escalated for senior assessor review.',
    riskIndicators: [
      'Third claim on same policy within 30 days — fraud-risk indicator (Clause 0.6e)',
      'Claim amount EGP 45,000 exceeds EGP 10,000 auto-approval cap (Clause 0.2f)',
      'Remaining annual limit EGP 20,000 is below claimed amount EGP 45,000',
    ],
    handbookEvidence: [
      {
        clauseId: 'Clause 0.6(e)',
        title: 'Fraud-risk: frequent claims',
        evidence:
          'Third claim on POL-M-2023-045 within 30 days. Previous: CLM-M-001 on 2024-01-28 (collision, EGP 3,200) and CLM-M-002 on 2024-02-05 (windscreen, EGP 900).',
        reason: 'Fraud-risk indicator — auto-approval blocked',
      },
      {
        clauseId: 'Clause 0.3',
        title: 'Claims above cap',
        evidence: 'EGP 45,000 exceeds EGP 10,000 cap. Mandatory human assessor approval required.',
        reason: 'Cap exceeded',
      },
      {
        clauseId: 'Clause 2.1',
        title: 'Motor theft cover',
        evidence: 'Theft of the insured vehicle is covered under comprehensive policy. Police report and spare key required.',
        reason: 'Coverage subject to fraud-risk review',
      },
      {
        clauseId: 'Clause 2.9',
        title: 'Theft waiting period',
        evidence: 'Theft cover begins 7 days after policy start (2023-03-15). Incident 2024-02-18 — waiting period satisfied.',
        reason: 'Waiting period satisfied',
      },
    ],
    extractedData: {
      claimType: 'Motor Theft',
      incidentDate: '2024-02-18',
      amount: 45000,
      vehicle: 'Toyota Corolla 2021, White',
      plateNumber: 'CAI-45213',
      policeReportNumber: 'PR-CAI-2024-00892',
      confidence: 0.91,
    },
    policyInfo: {
      number: 'POL-M-2023-045',
      productLine: 'MOTOR',
      status: 'ACTIVE',
      annualLimit: 80000,
      remainingLimit: 20000,
      deductible: 1000,
      riders: [],
    },
    documents: [
      { type: 'Police Theft Report', fileName: 'police_report_pr2024_00892.pdf', status: 'VERIFIED' },
      { type: 'Spare Key', fileName: 'spare_key_photo.jpg', status: 'VERIFIED' },
      { type: 'Vehicle Registration', fileName: 'vehicle_registration_corolla.pdf', status: 'VERIFIED' },
    ],
    auditTrail: [
      { action: 'CLAIM_CREATED', timestamp: '2024-02-19 11:30', actor: 'Customer', details: 'Claim submitted by Omar Farouk' },
      { action: 'DOCUMENT_UPLOADED', timestamp: '2024-02-19 11:35', actor: 'Customer', details: '3 documents uploaded' },
      { action: 'OCR_COMPLETED', timestamp: '2024-02-19 11:40', actor: 'System', details: 'OCR extraction confidence: 91%' },
      { action: 'REQUIRED_DOCUMENTS_CHECK', timestamp: '2024-02-19 11:40', actor: 'System', details: 'All required documents present' },
      { action: 'POLICY_VALIDATED', timestamp: '2024-02-19 11:41', actor: 'System', details: 'Policy ACTIVE. Theft waiting period (7 days from 2023-03-15) satisfied.' },
      { action: 'COVERAGE_CHECKED', timestamp: '2024-02-19 11:41', actor: 'System', details: 'Coverage confirmed under Clause 2.1. Subject to risk review.' },
      { action: 'RISK_CHECKED', timestamp: '2024-02-19 11:41', actor: 'System', details: 'FRAUD-RISK: 3rd claim within 30 days (Clause 0.6e). Amount > cap. Remaining limit EGP 20,000 < EGP 45,000.' },
      { action: 'DECISION_MADE', timestamp: '2024-02-19 11:41', actor: 'System', details: 'ESCALATE — multiple risk indicators. Senior assessor review required.' },
    ],
  },
  {
    id: 'clm-006',
    customerName: 'Nour El-Din Mahmoud',
    policyNumber: 'POL-P-2023-112',
    productLine: 'PROPERTY',
    claimType: 'Accidental Damage',
    claimedAmount: 8800,
    incidentDate: '2024-02-22',
    submittedDate: '2024-02-23',
    status: 'UNDER_HUMAN_REVIEW',
    riskStatus: 'MEDIUM',
    description:
      'Kitchen fire resulting from short circuit in the electrical panel. Damage to kitchen surfaces, appliances, and adjacent living room wall.',
    aiRecommendation: 'ROUTE_TO_HUMAN',
    aiReason:
      'Handbook retrieval returned conflicting evidence on Clause 3.1 (fire covered) vs. Clause 3.3 (gradual damage excluded). OCR text noted "ongoing electrical issue" — classification as sudden vs. gradual requires human judgment.',
    riskIndicators: ['Insufficient coverage evidence — Clause 3.1 vs. 3.3 conflict requires human judgment'],
    handbookEvidence: [
      {
        clauseId: 'Clause 3.1',
        title: 'Property fire cover',
        evidence: 'Fire is an explicitly covered peril under property insurance. Applies to building and contents.',
        reason: 'Fire covered — applies if sudden',
      },
      {
        clauseId: 'Clause 3.3',
        title: 'Gradual damage exclusion',
        evidence:
          'Gradual deterioration is excluded. OCR extracted phrase "ongoing electrical issue for several months" from the loss notice — warrants human review of whether this is sudden or gradual.',
        reason: 'Potential gradual-damage exclusion — ambiguous',
      },
    ],
    extractedData: {
      claimType: 'Property Fire / Accidental Damage',
      incidentDate: '2024-02-22',
      amount: 8800,
      property: 'Apartment 5C, Building 12, Maadi, Cairo',
      cause: 'Electrical fire — suspected short circuit in distribution panel',
      affectedRooms: 'Kitchen and adjacent living room wall',
      confidence: 0.84,
    },
    policyInfo: {
      number: 'POL-P-2023-112',
      productLine: 'PROPERTY',
      status: 'ACTIVE',
      annualLimit: 150000,
      remainingLimit: 150000,
      deductible: 2000,
      riders: [],
    },
    documents: [
      { type: 'Photos of Damage', fileName: 'fire_damage_photos_feb2024.zip', status: 'VERIFIED' },
      { type: 'Itemised List', fileName: 'damaged_items_list.pdf', status: 'VERIFIED' },
      { type: 'Repair / Replacement Quotations', fileName: 'repair_quotes_contractor.pdf', status: 'VERIFIED' },
    ],
    auditTrail: [
      { action: 'CLAIM_CREATED', timestamp: '2024-02-23 14:00', actor: 'Customer', details: 'Claim submitted by Nour El-Din Mahmoud' },
      { action: 'DOCUMENT_UPLOADED', timestamp: '2024-02-23 14:05', actor: 'Customer', details: '3 documents uploaded' },
      { action: 'OCR_COMPLETED', timestamp: '2024-02-23 14:12', actor: 'System', details: 'Extraction confidence: 84% (lower due to photo quality)' },
      { action: 'HANDBOOK_RETRIEVED', timestamp: '2024-02-23 14:13', actor: 'System', details: 'RAG retrieved Clauses 3.1 and 3.3 with conflicting signals' },
      { action: 'COVERAGE_CHECKED', timestamp: '2024-02-23 14:13', actor: 'System', details: 'Insufficient evidence — Clause 3.3 ambiguity detected in extracted text' },
      { action: 'DECISION_MADE', timestamp: '2024-02-23 14:13', actor: 'System', details: 'ROUTE_TO_HUMAN — insufficient handbook evidence for deterministic decision' },
    ],
  },
];

export const REQUIRED_DOCUMENTS: Record<string, Record<string, string[]>> = {
  HEALTH: {
    'Inpatient Hospitalisation': ['Medical Report', 'Itemised Hospital Invoice', 'Member ID'],
    'Day-Case Surgery': ['Medical Report', 'Itemised Hospital Invoice', 'Member ID'],
    'Diagnostics': ['Referring Physician Request', 'Itemised Invoice', 'Member ID'],
    'Medication': ['Prescription', 'Pharmacy Invoice', 'Member ID'],
    'Emergency Treatment': ['Medical Report', 'Itemised Invoice', 'Member ID'],
    'Outpatient Consultation': ['Medical Report', 'Member ID'],
    'Maternity': ['Medical Report', 'Itemised Hospital Invoice', 'Member ID'],
    'Dental': ['Medical Report', 'Itemised Invoice', 'Member ID'],
  },
  MOTOR: {
    'Collision': ['Photos of Damage', 'Repair Estimate', "Driver's Licence", 'Vehicle Registration'],
    'Fire': ['Photos of Damage', 'Fire Brigade Report', 'Vehicle Registration'],
    'Theft': ['Police Theft Report', 'Spare Key', 'Vehicle Registration'],
    'Third-Party': ['Police Report', 'Photos of Damage', 'Third-Party Details'],
    'Windscreen / Glass': ['Photos of Damage', 'Repair Estimate', 'Vehicle Registration'],
  },
  PROPERTY: {
    'Fire': ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'],
    'Lightning': ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'],
    'Explosion': ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'],
    'Accidental Damage': ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'],
    'Theft': ['Police Report (Forced Entry)', 'Itemised List', 'Proof of Ownership'],
    'Burst Internal Pipe': ['Photos of Damage', 'Plumber Report', 'Itemised List'],
    'Flood': ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'],
  },
  TRAVEL: {
    'Emergency Medical': ['Physician Report', 'Itemised Invoices'],
    'Trip Cancellation': ['Proof of Covered Reason'],
    'Baggage Loss': ['Airline PIR or Police Report', 'Receipts / Proof of Ownership'],
    'Baggage Delay': ['Airline Property Irregularity Report', 'Receipts for Essentials'],
    'Travel Document Replacement': ['Police Report', 'Embassy / Consulate Statement'],
  },
};

export const CLAIM_TYPES: Record<string, string[]> = {
  HEALTH: [
    'Inpatient Hospitalisation',
    'Day-Case Surgery',
    'Diagnostics',
    'Medication',
    'Emergency Treatment',
    'Outpatient Consultation',
    'Maternity',
    'Dental',
  ],
  MOTOR: ['Collision', 'Fire', 'Theft', 'Third-Party', 'Windscreen / Glass'],
  PROPERTY: ['Fire', 'Lightning', 'Explosion', 'Accidental Damage', 'Theft', 'Burst Internal Pipe', 'Flood'],
  TRAVEL: ['Emergency Medical', 'Trip Cancellation', 'Baggage Loss', 'Baggage Delay', 'Travel Document Replacement'],
};

export const OPERATIONS_DATA = {
  HEALTH: { processed: 234, approved: 187, routed: 28, rejected: 15, riskFlagged: 4 },
  MOTOR: { processed: 156, approved: 89, routed: 47, rejected: 18, riskFlagged: 2 },
  PROPERTY: { processed: 67, approved: 42, routed: 18, rejected: 7, riskFlagged: 0 },
  TRAVEL: { processed: 43, approved: 31, routed: 8, rejected: 4, riskFlagged: 0 },
};

export const VERIFICATION_POLICIES: Policy[] = [
  ...CUSTOMER_POLICIES,
  {
    id: 'pol-h-2021-099',
    number: 'POL-H-2021-099',
    productLine: 'HEALTH',
    status: 'CANCELLED',
    startDate: '2021-06-01',
    endDate: '2022-05-31',
    annualLimit: 30000,
    remainingLimit: 0,
    deductible: 500,
    riders: [],
  },
];
