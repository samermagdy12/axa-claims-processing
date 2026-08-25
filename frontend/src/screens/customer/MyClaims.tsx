import { useState } from 'react';
import { Card, Button, ClaimStatusBadge, ProductBadge, PageHeader, Amount, EmptyState, Alert, Spinner } from '../../components/UI';
import { useCustomerData } from '../../hooks/useCustomerData';
import type { Screen, ClaimStatus } from '../../types';

interface MyClaimsProps {
  navigate: (screen: Screen, params?: Record<string, string>) => void;
  token: string;
}

const STATUS_FILTERS: { label: string; value: ClaimStatus | 'ALL' }[] = [
  { label: 'All', value: 'ALL' },
  { label: 'Processing', value: 'PROCESSING' },
  { label: 'Docs Required', value: 'WAITING_FOR_DOCUMENTS' },
  { label: 'Human Review', value: 'UNDER_HUMAN_REVIEW' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Rejected', value: 'REJECTED' },
  { label: 'Below Deductible', value: 'BELOW_DEDUCTIBLE' },
];

export default function MyClaims({ navigate, token }: MyClaimsProps) {
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | 'ALL'>('ALL');
  const { claims, loading, error } = useCustomerData(token);

  const filtered = statusFilter === 'ALL'
    ? claims
    : claims.filter(c => c.status === statusFilter);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="My Claims"
        subtitle={`${claims.length} claims total`}
        action={<Button onClick={() => navigate('new-claim')}>+ New Claim</Button>}
      />

      {/* Status filter */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {STATUS_FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              statusFilter === f.value
                ? 'bg-axa-blue text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            {f.label}
            {f.value !== 'ALL' && (
              <span className="ml-1.5 text-[10px]">
                {claims.filter(c => c.status === f.value).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? <Card className="p-6 flex justify-center"><Spinner /></Card> : error ? <Alert variant="error">{error}</Alert> : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon="📋"
            title="No claims found"
            description="No claims match the selected filter."
            action={<Button variant="outline" onClick={() => setStatusFilter('ALL')}>Clear filter</Button>}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map(claim => (
            <Card
              key={claim.id}
              onClick={() => navigate('claim-details', { selectedClaimId: claim.id })}
            >
              <div className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-xs font-mono text-gray-400">{claim.id.toUpperCase()}</p>
                    </div>
                    <h3 className="text-base font-semibold text-gray-900">{claim.claimType}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">Policy: {claim.policyNumber}</p>
                  </div>

                  <div className="flex flex-col items-end gap-1.5">
                    <ClaimStatusBadge status={claim.status} />
                    <Amount value={claim.claimedAmount} />
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-gray-100">
                  <ProductBadge line={claim.productLine} />
                  <span className="text-xs text-gray-400">Incident: {claim.incidentDate}</span>
                  <span className="text-xs text-gray-400">Submitted: {claim.submissionDate}</span>
                </div>

                {/* Status-specific info */}
                {claim.status === 'WAITING_FOR_DOCUMENTS' && claim.decision?.missingDocuments && (
                  <Alert variant="warning" title="Documents required" className="mt-3">
                    <div className="mt-1 space-y-0.5">
                      {claim.decision.missingDocuments.map(d => (
                        <p key={d}>· {d}</p>
                      ))}
                    </div>
                    <Button size="sm" className="mt-2" onClick={e => { e.stopPropagation(); navigate('claim-details', { selectedClaimId: claim.id }); }}>
                      Upload Missing Documents
                    </Button>
                  </Alert>
                )}

                {claim.status === 'APPROVED' && claim.decision && (
                  <div className="mt-3 flex items-center gap-3 p-3 bg-emerald-50 rounded-lg">
                    <span className="text-emerald-600 font-bold text-lg">✓</span>
                    <div>
                      <p className="text-sm font-semibold text-emerald-800">Approved</p>
                      {claim.decision.approvedAmount && (
                        <p className="text-xs text-emerald-700">
                          EGP {claim.decision.approvedAmount.toLocaleString()} approved
                          {claim.decision.deductible ? ` (after EGP ${claim.decision.deductible} deductible)` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {claim.status === 'REJECTED' && claim.decision && (
                  <div className="mt-3 p-3 bg-red-50 rounded-lg">
                    <p className="text-sm font-semibold text-red-800">Rejected</p>
                    {claim.decision.reason && <p className="text-xs text-red-700 mt-0.5">{claim.decision.reason}</p>}
                  </div>
                )}

                {claim.status === 'PROCESSING' && (
                  <div className="mt-3 flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                    <span className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin-slow" />
                    <p className="text-sm text-blue-700">Your claim is being processed</p>
                  </div>
                )}

                {claim.status === 'UNDER_HUMAN_REVIEW' && (
                  <div className="mt-3 p-3 bg-violet-50 rounded-lg">
                    <p className="text-sm text-violet-800">
                      Your claim is under review by a certified assessor. You will be notified when a decision is made.
                    </p>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
