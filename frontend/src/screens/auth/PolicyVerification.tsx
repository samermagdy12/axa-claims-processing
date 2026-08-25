import { useState } from 'react';
import { Button, Card, PolicyStatusBadge, ProductBadge, Alert, AxaLogo, Amount } from '../../components/UI';
import { VERIFICATION_POLICIES } from '../../data';
import type { Policy } from '../../types';

interface PolicyVerificationProps {
  userName: string;
  nationalId: string;
  onComplete: () => void;
}

export default function PolicyVerification({ userName, nationalId, onComplete }: PolicyVerificationProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitted, setSubmitted] = useState(false);

  const toggle = (id: string) =>
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const handleConfirm = () => {
    if (selected.size === 0) return;
    setSubmitted(true);
    setTimeout(onComplete, 1200);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-3xl">✓</div>
        <h2 className="text-xl font-bold text-gray-900">Account Created</h2>
        <p className="text-gray-500 text-sm">{selected.size} {selected.size === 1 ? 'policy' : 'policies'} linked to your account.</p>
        <p className="text-gray-400 text-sm">Redirecting to your dashboard…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-axa-blue px-8 py-4">
        <AxaLogo light />
      </header>

      <div className="flex-1 flex items-start justify-center px-4 py-10">
        <div className="w-full max-w-2xl">
          {/* Progress */}
          <div className="flex items-center gap-3 mb-8">
            {['Account Details', 'Policy Verification', 'Complete'].map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                {i > 0 && <div className="flex-1 h-px w-8" style={{ background: i <= 1 ? '#00008F' : '#D1D5DB' }} />}
                <div className={`flex items-center gap-2 ${i <= 1 ? 'text-axa-blue' : 'text-gray-400'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    i === 0 ? 'bg-emerald-500 text-white' : i === 1 ? 'bg-axa-blue text-white' : 'border-2 border-gray-300 text-gray-400'
                  }`}>
                    {i === 0 ? '✓' : i + 1}
                  </div>
                  <span className="text-xs font-medium hidden sm:block">{step}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
            <div className="mb-6">
              <h1 className="text-xl font-bold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>
                Verify your policies
              </h1>
              <p className="text-sm text-gray-500">
                Welcome, <strong>{userName}</strong>. The following policies are associated with National ID{' '}
                <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                  {nationalId.replace(/(\d{4})(\d{6})(\d{4})/, '$1••••••$3')}
                </span>
                . Select all policies that belong to you.
              </p>
            </div>

            <Alert variant="info" title="Policy verification">
              We found {VERIFICATION_POLICIES.length} policies linked to your National ID. Inactive policies are shown with a warning — you can still select them to link them to your account.
            </Alert>

            <div className="mt-5 space-y-3">
              {VERIFICATION_POLICIES.map((policy: Policy) => {
                const isSelected = selected.has(policy.id);
                const isInactive = policy.status !== 'ACTIVE';
                return (
                  <div
                    key={policy.id}
                    onClick={() => toggle(policy.id)}
                    className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${
                      isSelected ? 'border-axa-blue bg-axa-blue-50' : isInactive ? 'border-amber-200 bg-amber-50/50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-axa-blue border-axa-blue' : 'border-gray-300'
                      }`}>
                        {isSelected && <span className="text-white text-xs font-bold">✓</span>}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="font-mono text-xs font-semibold text-gray-800">{policy.number}</span>
                          <ProductBadge line={policy.productLine} />
                          <PolicyStatusBadge status={policy.status} />
                          {isInactive && (
                            <span className="text-xs text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full font-medium">
                              ⚠ Policy not in force
                            </span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1 text-xs text-gray-500">
                          <span>Start: <strong className="text-gray-700">{policy.startDate}</strong></span>
                          <span>End: <strong className="text-gray-700">{policy.endDate}</strong></span>
                          <span>Annual limit: <strong className="text-gray-700"><Amount value={policy.annualLimit} size="sm" /></strong></span>
                          <span>Remaining: <strong className="text-gray-700"><Amount value={policy.remainingLimit} size="sm" /></strong></span>
                          <span>Deductible: <strong className="text-gray-700"><Amount value={policy.deductible} size="sm" /></strong></span>
                          {policy.riders.length > 0 && (
                            <span>Riders: <strong className="text-gray-700">{policy.riders.join(', ')}</strong></span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                {selected.size === 0 ? 'No policies selected' : `${selected.size} ${selected.size === 1 ? 'policy' : 'policies'} selected`}
              </p>
              <Button onClick={handleConfirm} disabled={selected.size === 0} size="lg">
                Confirm & Create Account
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
