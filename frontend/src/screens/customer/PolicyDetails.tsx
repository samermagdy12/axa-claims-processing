import { Button, ProductBadge, PolicyStatusBadge, ClaimStatusBadge, PageHeader, Amount, ProgressBar, Alert, DataRow, Card } from '../../components/UI';
import { useCustomerData } from '../../hooks/useCustomerData';
import type { Screen } from '../../types';

interface PolicyDetailsProps {
  policyId: string;
  token: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function PolicyDetails({ policyId, token, navigate }: PolicyDetailsProps) {
  const { policies, claims, loading, error } = useCustomerData(token);
  const policy = policies.find(p => p.id === policyId);
  if (loading) return <div className="p-6 text-gray-500">Loading policy…</div>;
  if (error) return <div className="p-6"><Alert variant="error">{error}</Alert></div>;
  if (!policy) return (
    <div className="p-6">
      <p className="text-red-600">Policy not found.</p>
      <Button variant="ghost" onClick={() => navigate('my-policies')}>← Back</Button>
    </div>
  );

  const policyClaims = claims.filter(c => c.policyId === policyId);
  const isInactive = policy.status !== 'ACTIVE';
  const usedAmt = policy.annualLimit - policy.remainingLimit;
  const usedPct = policy.annualLimit > 0 ? (usedAmt / policy.annualLimit) * 100 : 0;

  const PRODUCT_DESCRIPTIONS: Record<string, string> = {
    HEALTH: 'Health Insurance',
    MOTOR: 'Motor Insurance',
    PROPERTY: 'Property & Home Insurance',
    TRAVEL: 'Travel Insurance',
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        title={policy.number}
        subtitle={PRODUCT_DESCRIPTIONS[policy.productLine]}
        back={{ label: 'My Policies', onClick: () => navigate('my-policies') }}
        action={
          policy.status === 'ACTIVE' ? (
            <Button onClick={() => navigate('new-claim', { selectedPolicyId: policy.id })}>
              + File Claim
            </Button>
          ) : undefined
        }
      />

      {isInactive && (
        <Alert variant="warning" title={`Policy ${policy.status.toLowerCase()} — not in force`}>
          This policy is not currently active. Claims cannot be submitted against this policy (Handbook Clause 0.8). Contact AXA Egypt to reinstate or renew your policy.
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-5">
        {/* Main details */}
        <div className="lg:col-span-2 space-y-5">
          {/* Header card */}
          <Card className="p-5">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${
                policy.productLine === 'HEALTH' ? 'bg-emerald-100' :
                policy.productLine === 'MOTOR' ? 'bg-blue-100' :
                policy.productLine === 'PROPERTY' ? 'bg-amber-100' : 'bg-violet-100'
              }`}>
                {policy.productLine === 'HEALTH' ? '🏥' : policy.productLine === 'MOTOR' ? '🚗' : policy.productLine === 'PROPERTY' ? '🏠' : '✈️'}
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <ProductBadge line={policy.productLine} />
                  <PolicyStatusBadge status={policy.status} />
                </div>
                <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>{policy.number}</p>
                <p className="text-xs text-gray-500 font-mono">Policy ID: {policy.id}</p>
              </div>
            </div>
          </Card>

          {/* Policy details */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Policy Details</h3>
            <DataRow label="Policy number" value={<span className="font-mono">{policy.number}</span>} />
            <DataRow label="Product line" value={<ProductBadge line={policy.productLine} />} />
            <DataRow label="Status" value={<PolicyStatusBadge status={policy.status} />} />
            <DataRow label="Start date" value={policy.startDate} />
            <DataRow label="End date" value={policy.endDate} />
            <DataRow label="Annual limit" value={<Amount value={policy.annualLimit} />} />
            <DataRow label="Remaining limit" value={<Amount value={policy.remainingLimit} />} />
            <DataRow label="Deductible" value={<Amount value={policy.deductible} />} />
          </Card>

          {/* Riders */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Policy Riders</h3>
            {policy.riders.length === 0 ? (
              <p className="text-sm text-gray-500">No riders on this policy.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {policy.riders.map(r => (
                  <span key={r} className="px-3 py-1.5 bg-axa-blue-50 text-axa-blue rounded-full text-sm font-semibold">{r}</span>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {/* Limit usage */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4" style={{ fontFamily: 'var(--font-display)' }}>Annual Limit</h3>
            <Amount value={policy.remainingLimit} size="xl" />
            <p className="text-xs text-gray-500 mb-3">remaining this year</p>
            <ProgressBar
              value={usedAmt}
              max={policy.annualLimit}
              colorClass={isInactive ? 'bg-gray-400' : usedPct > 80 ? 'bg-axa-red' : usedPct > 50 ? 'bg-amber-400' : 'bg-axa-blue'}
            />
            <div className="flex justify-between mt-2 text-xs text-gray-400">
              <span>EGP {usedAmt.toLocaleString()} used</span>
              <span>{usedPct.toFixed(0)}%</span>
            </div>
            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">Annual limit</p>
              <Amount value={policy.annualLimit} />
            </div>
          </Card>

          {/* Claims on this policy */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Claims</h3>
              <span className="text-xs text-gray-400">{policyClaims.length} total</span>
            </div>
            {policyClaims.length === 0 ? (
              <p className="text-sm text-gray-500">No claims on this policy.</p>
            ) : (
              <div className="space-y-2">
                {policyClaims.map(c => (
                  <button
                    key={c.id}
                    onClick={() => navigate('claim-details', { selectedClaimId: c.id })}
                    className="w-full text-left border border-gray-200 rounded-lg p-3 hover:border-axa-blue transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-gray-400">{c.id.toUpperCase()}</span>
                      <ClaimStatusBadge status={c.status} />
                    </div>
                    <p className="text-xs font-semibold text-gray-700 mt-1">{c.claimType}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{c.incidentDate} · <Amount value={c.claimedAmount} size="sm" /></p>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
