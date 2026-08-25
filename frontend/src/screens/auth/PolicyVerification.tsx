import { useState } from 'react';
import { Button, PolicyStatusBadge, ProductBadge, Alert, AxaLogo, Amount } from '../../components/UI';
import { registerCustomer } from '../../api';
import type { Policy } from '../../types';

interface PolicyVerificationProps {
  account: { fullName: string; email: string; password: string; nationalId: string };
  policies: Policy[];
  onComplete: () => void;
  onGoSignIn: () => void;
}

export default function PolicyVerification({ account, policies, onComplete, onGoSignIn }: PolicyVerificationProps) {
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setSubmitError('');
    setIsSubmitting(true);
    try {
      await registerCustomer(account);
      setSubmitted(true);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Unable to create your account.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <header className="bg-axa-blue px-8 py-4"><AxaLogo light /></header>
        <div className="flex-1 flex items-start justify-center px-4 py-10">
          <div className="w-full max-w-md">
            <ProgressStep active={2} />
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-3xl mx-auto mb-4">✓</div>
              <h2 className="text-xl font-bold text-gray-900">Account Created</h2>
              <p className="text-gray-500 text-sm mt-2">Your verified policies remain associated with your account.</p>
              <Button onClick={() => { onComplete(); onGoSignIn(); }} className="w-full mt-6" size="lg">Proceed to Sign In</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-axa-blue px-8 py-4"><AxaLogo light /></header>
      <div className="flex-1 flex items-start justify-center px-4 py-10">
        <div className="w-full max-w-2xl">
          <ProgressStep active={1} />
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
            <div className="mb-6">
              <h1 className="text-xl font-bold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>Verify your policies</h1>
              <p className="text-sm text-gray-500">
                Welcome, <strong>{account.fullName}</strong>. The following policies are associated with National ID{' '}
                <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{account.nationalId.replace(/(\d{4})(\d{6})(\d{4})/, '$1••••••$3')}</span>.
              </p>
            </div>

            <Alert variant="info" title="Policy verification">We found {policies.length} {policies.length === 1 ? 'policy' : 'policies'} linked to your National ID. These records are shown for confirmation only and cannot be changed here.</Alert>

            <div className="mt-5 space-y-3">
              {policies.map((policy) => {
                const isInactive = policy.status !== 'ACTIVE';
                return (
                  <div key={policy.id} className={`border-2 rounded-xl p-4 ${isInactive ? 'border-amber-200 bg-amber-50/50' : 'border-gray-200'}`}>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded border-2 border-axa-blue bg-axa-blue flex-shrink-0 mt-0.5 flex items-center justify-center"><span className="text-white text-xs font-bold">✓</span></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="font-mono text-xs font-semibold text-gray-800">{policy.number}</span>
                          <ProductBadge line={policy.productLine} />
                          <PolicyStatusBadge status={policy.status} />
                          {isInactive && <span className="text-xs text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full font-medium">⚠ Policy not in force</span>}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1 text-xs text-gray-500">
                          <span>Start: <strong className="text-gray-700">{policy.startDate}</strong></span>
                          <span>End: <strong className="text-gray-700">{policy.endDate}</strong></span>
                          <span>Annual limit: <strong className="text-gray-700"><Amount value={policy.annualLimit} size="sm" /></strong></span>
                          <span>Remaining: <strong className="text-gray-700"><Amount value={policy.remainingLimit} size="sm" /></strong></span>
                          <span>Deductible: <strong className="text-gray-700"><Amount value={policy.deductible} size="sm" /></strong></span>
                          {policy.riders.length > 0 && <span>Riders: <strong className="text-gray-700">{policy.riders.join(', ')}</strong></span>}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {submitError && <Alert variant="error" className="mt-5">{submitError}</Alert>}
            <div className="mt-6 flex justify-end"><Button onClick={handleConfirm} loading={isSubmitting} size="lg">Confirm & Create Account</Button></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProgressStep({ active }: { active: number }) {
  return (
    <div className="flex items-center gap-3 mb-8">
      {['Account Details', 'Policy Verification', 'Complete'].map((step, i) => (
        <div key={step} className="flex items-center gap-2">
          {i > 0 && <div className="flex-1 h-px w-8" style={{ background: i <= active ? '#00008F' : '#D1D5DB' }} />}
          <div className={`flex items-center gap-2 ${i <= active ? 'text-axa-blue' : 'text-gray-400'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i < active ? 'bg-emerald-500 text-white' : i === active ? 'bg-axa-blue text-white' : 'border-2 border-gray-300 text-gray-400'}`}>{i < active ? '✓' : i + 1}</div>
            <span className="text-xs font-medium hidden sm:block">{step}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
