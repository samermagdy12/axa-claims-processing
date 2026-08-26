import type { Claim, Policy } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface AuthSession {
  access_token: string;
  token_type: 'bearer';
  user: { user_id: string; full_name: string; email: string; role: string };
}

export interface CreatedClaim {
  claim_id: string;
  policy_id: string;
  claim_type: string;
  incident_date: string;
  submission_date: string;
  claimed_amount: number;
  description: string | null;
  status: string;
  required_documents: { claim_required_document_id: string; document_type: string; is_required: boolean; status: 'MISSING' | 'UPLOADED' | 'VERIFIED' }[];
}

export interface UploadedClaimDocument {
  document_id: string;
  claim_id: string;
  document_type: string;
  original_file_name: string;
  mime_type: string;
  file_size_bytes: number;
  uploaded_at: string;
  required_document: { claim_required_document_id: string; document_type: string; is_required: boolean; status: 'MISSING' | 'UPLOADED' | 'VERIFIED' };
  claim_status: Claim['status'];
}

export interface DocumentExtraction {
  extraction_id: string;
  claim_id: string;
  document_id: string;
  document_type: string;
  strategy: string;
  text_length: number;
  extraction_confidence: number | null;
  extracted_at: string;
  reused: boolean;
  validation: DocumentValidation;
}

export interface DocumentValidation {
  status: 'valid' | 'invalid' | 'warning' | 'pending' | 'failed';
  document_valid: boolean | null;
  message: string;
  errors: string[];
  warnings: string[];
  expected_document_type: string | null;
  detected_document_type: string | null;
}
export interface FinalDecision {
  claim_id: string;
  llm_recommendation: 'settle' | 'request_documents' | 'reject' | 'route_to_human';
  final_decision: 'settle' | 'request_documents' | 'reject' | 'route_to_human';
  decision_source: 'business_rules'; auto_processed: boolean; human_review_required: boolean;
  triggered_rules: { rule_id: string; outcome: string; reason: string }[];
  reason: string; missing_documents: string[]; customer_message: string;
  handbook_references: { chunk_id: string; rule_identifier?: string | null; section?: string | null }[];
}

type ApiClaim = {
  claim_id: string; policy_id: string; policy_number: string; product_line: Claim['productLine'];
  claim_type: string; incident_date: string; submission_date: string; claimed_amount: number;
  description: string | null; status: Claim['status'];
  final_decision?: { final_decision: string; reason?: string | null; customer_message?: string | null; handbook_clause?: string | null } | null;
  required_documents?: { document_type: string; status: 'MISSING' | 'UPLOADED' | 'VERIFIED'; original_file_name?: string | null }[];
};

type ApiPolicy = {
  policy_id: string; policy_number: string; product_line: Policy['productLine']; status: Policy['status'];
  start_date: string; end_date: string; annual_limit: number; remaining_limit: number; deductible: number; riders: string[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || 'Something went wrong. Please try again.');
  }
  return response.json() as Promise<T>;
}

export function registerCustomer(data: { fullName: string; email: string; password: string; nationalId: string }) {
  return request<AuthSession>('/auth/register', { method: 'POST', body: JSON.stringify({ full_name: data.fullName, email: data.email, password: data.password, national_id: data.nationalId }) });
}
export async function verifyPolicies(nationalId: string): Promise<Policy[]> {
  return (await request<ApiPolicy[]>('/auth/verify-policies', {
    method: 'POST',
    body: JSON.stringify({ national_id: nationalId }),
  })).map(toPolicy);
}
export function login(data: { email: string; password: string }) { return request<AuthSession>('/auth/login', { method: 'POST', body: JSON.stringify(data) }); }
function toPolicy(policy: ApiPolicy): Policy { return { id: policy.policy_id, number: policy.policy_number, productLine: policy.product_line, status: policy.status, startDate: policy.start_date, endDate: policy.end_date, annualLimit: Number(policy.annual_limit), remainingLimit: Number(policy.remaining_limit), deductible: Number(policy.deductible), riders: policy.riders }; }
function toClaim(claim: ApiClaim): Claim {
  const documents = (claim.required_documents || []).map(document => ({ type: document.document_type, status: document.status, fileName: document.original_file_name || undefined }));
  return {
    id: claim.claim_id, policyId: claim.policy_id, policyNumber: claim.policy_number,
    productLine: claim.product_line, claimType: claim.claim_type, incidentDate: claim.incident_date,
    submissionDate: claim.submission_date, claimedAmount: Number(claim.claimed_amount),
    description: claim.description || '', status: claim.status, documents,
    decision: claim.final_decision ? { outcome: claim.final_decision.final_decision, reason: claim.final_decision.reason || undefined, customerMessage: claim.final_decision.customer_message || undefined, handbookClause: claim.final_decision.handbook_clause || undefined, missingDocuments: documents.filter(document => document.status === 'MISSING').map(document => document.type) } : claim.status === 'WAITING_FOR_DOCUMENTS' ? { outcome: 'request_documents', missingDocuments: documents.filter(document => document.status === 'MISSING').map(document => document.type) } : undefined,
  };
}
export async function getMyPolicies(token: string): Promise<Policy[]> { return (await request<ApiPolicy[]>('/policies/my', { headers: { Authorization: `Bearer ${token}` } })).map(toPolicy); }
export async function getPolicy(policyId: string, token: string): Promise<Policy> { return toPolicy(await request<ApiPolicy>(`/policies/${encodeURIComponent(policyId)}`, { headers: { Authorization: `Bearer ${token}` } })); }
export async function getMyClaims(token: string): Promise<Claim[]> { return (await request<ApiClaim[]>('/claims/my', { headers: { Authorization: `Bearer ${token}` } })).map(toClaim); }
export async function getClaim(claimId: string, token: string): Promise<Claim> { return toClaim(await request<ApiClaim>(`/claims/${encodeURIComponent(claimId)}`, { headers: { Authorization: `Bearer ${token}` } })); }
export async function uploadClaimDocument(token: string, claimId: string, documentType: string, file: File): Promise<UploadedClaimDocument> {
  const form = new FormData();
  form.append('document_type', documentType);
  form.append('file', file);
  const response = await fetch(`${API_BASE_URL}/claims/${encodeURIComponent(claimId)}/documents`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || 'Unable to upload the document.');
  }
  return response.json() as Promise<UploadedClaimDocument>;
}
export function extractClaimDocument(token: string, claimId: string, documentId: string): Promise<DocumentExtraction> {
  return request<DocumentExtraction>(`/claims/${encodeURIComponent(claimId)}/documents/${encodeURIComponent(documentId)}/extract`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}
export function decideClaim(token: string, claimId: string): Promise<FinalDecision> {
  return request<FinalDecision>(`/claims/${encodeURIComponent(claimId)}/decide`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
}
export function removeClaimDocument(token: string, claimId: string, documentType: string): Promise<{ document_type: string; status: string }> {
  return request(`/claims/${encodeURIComponent(claimId)}/documents/${encodeURIComponent(documentType)}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
}
export function createClaim(token: string, data: { policyId: string; claimType: string; incidentDate: string; claimedAmount: number; description: string }) {
  return request<CreatedClaim>('/claims', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ policy_id: data.policyId, claim_type: data.claimType, incident_date: data.incidentDate, claimed_amount: data.claimedAmount, description: data.description }) });
}
