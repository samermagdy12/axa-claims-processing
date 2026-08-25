import { Card, Button, ClaimStatusBadge, PolicyStatusBadge, ProductBadge, Amount, ProgressBar, EmptyState, Alert, Spinner } from '../../components/UI';
import { useCustomerData } from '../../hooks/useCustomerData';
import type { Screen } from '../../types';

interface CustomerHomeProps {
  userName: string;
  token: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function CustomerHome({ userName, token, navigate }: CustomerHomeProps) {
  const { policies, claims, loading, error } = useCustomerData(token);
  const activePolicies = policies.filter(p => p.status === 'ACTIVE');
  const recentClaims = claims.slice(0, 4);
  const firstName = userName.split(' ')[0];

  return (
    <div className="animate-fade-in">
      {/* Welcome */}
      <div className="bg-axa-blue rounded-2xl px-7 py-6 mb-6 flex items-center justify-between">
        <div>
          <p className="text-white/70 text-sm">Welcome back</p>
          <h1 className="text-white text-2xl font-bold mt-0.5" style={{ fontFamily: 'var(--font-display)' }}>
            {firstName}
          </h1>
          <p className="text-white/60 text-sm mt-1">
            {activePolicies.length} active {activePolicies.length === 1 ? 'policy' : 'policies'} · {claims.length} claims
          </p>
        </div>
        <Button
          onClick={() => navigate('new-claim')}
          className="bg-white text-axa-blue hover:bg-axa-blue-100 shadow-none"
        >
          + New Claim
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policies column */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>My Policies</h2>
            <button onClick={() => navigate('my-policies')} className="text-sm text-axa-blue hover:underline">View all</button>
          </div>

          {loading ? <Card className="p-6 flex justify-center"><Spinner /></Card> : error ? <Alert variant="error">{error}</Alert> : policies.length === 0 ? <Card><EmptyState icon="📄" title="No policies found" description="There are no policies associated with your account." /></Card> : (
          <div className="space-y-3">
            {policies.map(policy => {
              const usedPct = ((policy.annualLimit - policy.remainingLimit) / policy.annualLimit) * 100;
              const isInactive = policy.status !== 'ACTIVE';
              return (
                <Card
                  key={policy.id}
                  onClick={() => navigate('policy-details', { selectedPolicyId: policy.id })}
                  className={isInactive ? 'border-amber-200' : ''}
                >
                  <div className="p-4">
                    {isInactive && (
                      <Alert variant="warning" title={`Policy ${policy.status.toLowerCase()}`}>
                        This policy is not in force. Claims cannot be created against this policy.
                      </Alert>
                    )}
                    <div className={`flex items-start justify-between ${isInactive ? 'mt-3' : ''}`}>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <ProductBadge line={policy.productLine} />
                          <PolicyStatusBadge status={policy.status} />
                        </div>
                        <p className="font-mono text-xs text-gray-500">{policy.number}</p>
                      </div>
                      <div className="text-right">
                        <Amount value={policy.remainingLimit} size="lg" />
                        <p className="text-xs text-gray-500">remaining of <span className="font-mono font-medium">EGP {policy.annualLimit.toLocaleString()}</span></p>
                      </div>
                    </div>

                    <div className="mt-3">
                      <ProgressBar
                        value={policy.annualLimit - policy.remainingLimit}
                        max={policy.annualLimit}
                        colorClass={isInactive ? 'bg-amber-400' : usedPct > 70 ? 'bg-axa-red' : 'bg-axa-blue'}
                      />
                      <div className="flex justify-between mt-1">
                        <span className="text-xs text-gray-400">{usedPct.toFixed(0)}% used</span>
                        <span className="text-xs text-gray-400">Deductible: EGP {policy.deductible.toLocaleString()}</span>
                      </div>
                    </div>

                    {policy.riders.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {policy.riders.map(r => (
                          <span key={r} className="text-xs bg-axa-blue-50 text-axa-blue px-2 py-0.5 rounded-full font-medium">{r}</span>
                        ))}
                      </div>
                    )}

                    <div className="flex gap-2 mt-3">
                      <span className="text-xs text-gray-400">{policy.startDate}</span>
                      <span className="text-xs text-gray-300">→</span>
                      <span className="text-xs text-gray-400">{policy.endDate}</span>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>)}
        </div>

        {/* Claims column */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Recent Claims</h2>
            <button onClick={() => navigate('my-claims')} className="text-sm text-axa-blue hover:underline">View all</button>
          </div>

          {loading ? <Card className="p-6 flex justify-center"><Spinner /></Card> : error ? <Alert variant="error">{error}</Alert> : recentClaims.length === 0 ? (
            <Card>
              <EmptyState icon="📋" title="No claims yet" description="Create your first claim when you need to." />
            </Card>
          ) : (
            <div className="space-y-3">
              {recentClaims.map(claim => (
                <Card key={claim.id} onClick={() => navigate('claim-details', { selectedClaimId: claim.id })} className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="text-xs font-mono text-gray-400">{claim.id.toUpperCase()}</p>
                      <p className="text-sm font-semibold text-gray-800 mt-0.5">{claim.claimType}</p>
                    </div>
                    <ClaimStatusBadge status={claim.status} />
                  </div>
                  <div className="flex items-center justify-between">
                    <ProductBadge line={claim.productLine} />
                    <Amount value={claim.claimedAmount} size="sm" />
                  </div>
                  <p className="text-xs text-gray-400 mt-2">{claim.incidentDate}</p>

                  {claim.status === 'WAITING_FOR_DOCUMENTS' && claim.decision?.missingDocuments && (
                    <div className="mt-2 p-2 bg-amber-50 rounded-lg">
                      <p className="text-xs font-medium text-amber-800 mb-1">Docs needed:</p>
                      {claim.decision.missingDocuments.map(d => (
                        <p key={d} className="text-xs text-amber-700">· {d}</p>
                      ))}
                    </div>
                  )}
                </Card>
              ))}

              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate('new-claim')}
              >
                + Submit New Claim
              </Button>
            </div>
          )}

          {/* Quick stats */}
          <div className="mt-4 bg-gray-100 rounded-xl p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Summary</p>
            <div className="space-y-2">
              {[
                { label: 'Total claims', value: claims.length },
                { label: 'Approved', value: claims.filter(c => c.status === 'APPROVED').length },
                { label: 'Processing', value: claims.filter(c => c.status === 'PROCESSING').length },
                { label: 'Pending docs', value: claims.filter(c => c.status === 'WAITING_FOR_DOCUMENTS').length },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">{label}</span>
                  <span className="text-sm font-bold text-gray-800">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
