import type { Policy } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface AuthSession {
  access_token: string;
  token_type: 'bearer';
  user: { user_id: string; full_name: string; email: string; role: string };
}

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
export function login(data: { email: string; password: string }) { return request<AuthSession>('/auth/login', { method: 'POST', body: JSON.stringify(data) }); }
function toPolicy(policy: ApiPolicy): Policy { return { id: policy.policy_id, number: policy.policy_number, productLine: policy.product_line, status: policy.status, startDate: policy.start_date, endDate: policy.end_date, annualLimit: Number(policy.annual_limit), remainingLimit: Number(policy.remaining_limit), deductible: Number(policy.deductible), riders: policy.riders }; }
export async function getMyPolicies(token: string): Promise<Policy[]> { return (await request<ApiPolicy[]>('/policies/my', { headers: { Authorization: `Bearer ${token}` } })).map(toPolicy); }
export async function getPolicy(policyId: string, token: string): Promise<Policy> { return toPolicy(await request<ApiPolicy>(`/policies/${encodeURIComponent(policyId)}`, { headers: { Authorization: `Bearer ${token}` } })); }
