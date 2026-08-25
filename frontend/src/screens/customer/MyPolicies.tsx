import { useEffect, useState } from 'react';
import { Card, Button, ProductBadge, PolicyStatusBadge, PageHeader, Amount, ProgressBar, Alert } from '../../components/UI';
import { getMyPolicies } from '../../api';
import type { Policy, Screen, ProductLine } from '../../types';

interface MyPoliciesProps {
  navigate: (screen: Screen, params?: Record<string, string>) => void;
  token: string;
}

const LINE_FILTERS: { label: string; value: ProductLine | 'ALL' }[] = [
  { label: 'All', value: 'ALL' },
  { label: 'Health', value: 'HEALTH' },
  { label: 'Motor', value: 'MOTOR' },
  { label: 'Property', value: 'PROPERTY' },
  { label: 'Travel', value: 'TRAVEL' },
];

export default function MyPolicies({ navigate, token }: MyPoliciesProps) {
  const [filter, setFilter] = useState<ProductLine | 'ALL'>('ALL');
  const [allPolicies, setAllPolicies] = useState<Policy[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getMyPolicies(token)
      .then(setAllPolicies)
      .catch(err => setError(err instanceof Error ? err.message : 'Unable to load policies.'))
      .finally(() => setIsLoading(false));
  }, [token]);

  const policies = filter === 'ALL' ? allPolicies : allPolicies.filter(p => p.productLine === filter);

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="My Policies"
        subtitle={`${allPolicies.length} policies linked to your account`}
        action={<Button onClick={() => navigate('new-claim')}>+ New Claim</Button>}
      />

      {/* Filter */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {LINE_FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filter === f.value
                ? 'bg-axa-blue text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-sm text-gray-500">Loading your policies…</p>}
      {error && <Alert variant="error">{error}</Alert>}
      {!isLoading && !error && policies.length === 0 && <Alert variant="info">No policies are assigned to your account.</Alert>}

      <div className="space-y-4">
        {policies.map(policy => {
          const isInactive = policy.status !== 'ACTIVE';
          const usedAmt = policy.annualLimit - policy.remainingLimit;
          const usedPct = policy.annualLimit > 0 ? (usedAmt / policy.annualLimit) * 100 : 0;

          return (
            <Card key={policy.id} className={isInactive ? 'border-amber-200' : ''}>
              <div className="p-5">
                {isInactive && (
                  <Alert variant="warning" title={`Policy ${policy.status.toLowerCase()}`}>
                    This policy is not in force. Claims cannot be submitted against an inactive policy (Clause 0.8).
                  </Alert>
                )}

                <div className={`flex flex-wrap items-start justify-between gap-4 ${isInactive ? 'mt-4' : ''}`}>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <ProductBadge line={policy.productLine} />
                      <PolicyStatusBadge status={policy.status} />
                    </div>
                    <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>
                      {policy.number}
                    </p>
                    <p className="text-xs text-gray-500 font-mono">ID: {policy.id}</p>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('policy-details', { selectedPolicyId: policy.id })}
                    >
                      View Details
                    </Button>
                    {policy.status === 'ACTIVE' && (
                      <Button
                        size="sm"
                        onClick={() => navigate('new-claim', { selectedPolicyId: policy.id })}
                      >
                        File Claim
                      </Button>
                    )}
                  </div>
                </div>

                {/* Limit bar */}
                <div className="mt-4">
                  <div className="flex justify-between items-end mb-1.5">
                    <span className="text-xs text-gray-500">Annual limit usage</span>
                    <div className="text-right">
                      <Amount value={policy.remainingLimit} size="lg" />
                      <span className="text-xs text-gray-400 ml-1">remaining</span>
                    </div>
                  </div>
                  <ProgressBar
                    value={usedAmt}
                    max={policy.annualLimit}
                    colorClass={isInactive ? 'bg-amber-300' : usedPct > 80 ? 'bg-axa-red' : usedPct > 50 ? 'bg-amber-400' : 'bg-axa-blue'}
                  />
                  <div className="flex justify-between mt-1">
                    <span className="text-xs text-gray-400">
                      EGP {usedAmt.toLocaleString()} used of EGP {policy.annualLimit.toLocaleString()}
                    </span>
                    <span className="text-xs text-gray-400">{usedPct.toFixed(0)}%</span>
                  </div>
                </div>

                {/* Details grid */}
                <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { label: 'Start date', value: policy.startDate },
                    { label: 'End date', value: policy.endDate },
                    { label: 'Deductible', value: `EGP ${policy.deductible.toLocaleString()}` },
                    { label: 'Riders', value: policy.riders.length > 0 ? policy.riders.join(', ') : 'None' },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-gray-50 rounded-lg p-3">
                      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                      <p className="text-sm font-semibold text-gray-800">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
