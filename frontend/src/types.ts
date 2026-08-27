export type ProductLine = 'HEALTH' | 'MOTOR' | 'PROPERTY' | 'TRAVEL';
export type PolicyStatus = 'ACTIVE' | 'LAPSED' | 'CANCELLED' | 'PENDING';
export type ClaimStatus =
  | 'PROCESSING'
  | 'WAITING_FOR_DOCUMENTS'
  | 'UNDER_HUMAN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'ROUTED'
  | 'ESCALATED'
  | 'BELOW_DEDUCTIBLE'
  | 'CLOSED';
export type DocStatus = 'MISSING' | 'UPLOADED' | 'VERIFIED';
export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
export type Role = 'customer' | 'assessor' | 'operations';

export interface Policy {
  id: string;
  number: string;
  productLine: ProductLine;
  status: PolicyStatus;
  startDate: string;
  endDate: string;
  annualLimit: number;
  remainingLimit: number;
  deductible: number;
  riders: string[];
}

export interface ClaimDocument {
  type: string;
  fileName?: string;
  status: DocStatus;
}

export interface Decision {
  outcome: string;
  approvedAmount?: number;
  deductible?: number;
  reason?: string;
  handbookClause?: string;
  missingDocuments?: string[];
  customerMessage?: string;
  decisionTrace?: { rule: string; result: 'passed' | 'failed' | 'skipped'; details: string }[];
  llmRecommendation?: string;
}

export interface Claim {
  id: string;
  policyId: string;
  policyNumber: string;
  productLine: ProductLine;
  claimType: string;
  incidentDate: string;
  submissionDate: string;
  claimedAmount: number;
  description: string;
  status: ClaimStatus;
  decision?: Decision;
  documents: ClaimDocument[];
}

export interface HandbookEvidence {
  clauseId: string;
  title: string;
  evidence: string;
  reason: string;
}

export interface AuditEntry {
  action: string;
  timestamp: string;
  actor: string;
  details: string;
}

export interface ExtractedData {
  claimType: string;
  incidentDate: string;
  amount: number;
  confidence: number;
  [key: string]: unknown;
}

export interface AssessorClaim {
  id: string;
  customerName: string;
  policyNumber: string;
  productLine: ProductLine;
  claimType: string;
  claimedAmount: number;
  incidentDate: string;
  submittedDate: string;
  status: ClaimStatus;
  riskStatus: RiskLevel;
  aiRecommendation: string;
  aiReason: string;
  riskIndicators: string[];
  handbookEvidence: HandbookEvidence[];
  extractedData: ExtractedData;
  policyInfo: {
    number: string;
    productLine: ProductLine;
    status: PolicyStatus;
    annualLimit: number;
    remainingLimit: number;
    deductible: number;
    riders: string[];
  };
  documents: ClaimDocument[];
  auditTrail: AuditEntry[];
  description?: string;
  humanDecision?: string;
  reviewReason?: string;
}

export interface NavigateParams {
  selectedPolicyId?: string;
  selectedClaimId?: string;
  selectedAssessorClaimId?: string;
  processingDocuments?: string;
  completedExtractions?: string;
  processingFailures?: string;
  processingValidationResults?: string;
}

export type Screen =
  | 'landing'
  | 'signup'
  | 'policy-verification'
  | 'customer-home'
  | 'my-policies'
  | 'policy-details'
  | 'my-claims'
  | 'new-claim'
  | 'claim-processing'
  | 'claim-details'
  | 'profile'
  | 'assessor-queue'
  | 'assessor-claims'
  | 'assessor-review'
  | 'operations';

export interface AppState {
  screen: Screen;
  role: Role | null;
  userId?: string;
  userName?: string;
  userEmail?: string;
  selectedPolicyId?: string;
  selectedClaimId?: string;
  selectedAssessorClaimId?: string;
  processingDocuments?: string;
  completedExtractions?: string;
  processingFailures?: string;
}
