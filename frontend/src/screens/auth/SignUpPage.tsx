import { useState } from 'react';
import { Button, Input, Alert, AxaLogo } from '../../components/UI';
import { registerCustomer } from '../../api';

interface SignUpPageProps {
  onComplete: () => void;
  onGoSignIn: () => void;
}

export default function SignUpPage({ onComplete, onGoSignIn }: SignUpPageProps) {
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirmPassword: '', nationalId: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(prev => ({ ...prev, [k]: e.target.value }));

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.fullName.trim()) e.fullName = 'Full name is required.';
    if (!form.email.includes('@')) e.email = 'Enter a valid email address.';
    if (form.password.length < 8) e.password = 'Password must be at least 8 characters.';
    if (form.password !== form.confirmPassword) e.confirmPassword = 'Passwords do not match.';
    if (!/^\d{14}$/.test(form.nationalId)) e.nationalId = 'National ID must be 14 digits.';
    return e;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setSubmitError('');
    setIsSubmitting(true);
    try { await registerCustomer(form); onComplete(); }
    catch (error) { setSubmitError(error instanceof Error ? error.message : 'Unable to create your account.'); }
    finally { setIsSubmitting(false); }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-axa-blue px-8 py-4">
        <AxaLogo light />
      </header>

      <div className="flex-1 flex items-start justify-center px-4 py-10">
        <div className="w-full max-w-md">
          {/* Progress */}
          <div className="flex items-center gap-3 mb-8">
            {['Account Details', 'Policy Verification', 'Complete'].map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                {i > 0 && <div className="flex-1 h-px bg-gray-300 w-8" />}
                <div className={`flex items-center gap-2 ${i === 0 ? 'text-axa-blue' : 'text-gray-400'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-axa-blue text-white' : 'border-2 border-gray-300 text-gray-400'}`}>
                    {i + 1}
                  </div>
                  <span className="text-xs font-medium hidden sm:block">{step}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
            <div className="mb-6">
              <h1 className="text-xl font-bold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>
                Create your account
              </h1>
              <p className="text-sm text-gray-500">Enter your details to register for AXA Egypt Claims.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Full Name"
                value={form.fullName}
                onChange={set('fullName')}
                placeholder="As it appears on your National ID"
                error={errors.fullName}
              />
              <Input
                label="Email Address"
                type="email"
                value={form.email}
                onChange={set('email')}
                placeholder="you@example.com"
                error={errors.email}
              />
              <Input
                label="National ID (14 digits)"
                value={form.nationalId}
                onChange={set('nationalId')}
                placeholder="29901152301234"
                maxLength={14}
                error={errors.nationalId}
                hint="Used to verify your insurance policies"
              />
              <Input
                label="Password"
                type="password"
                value={form.password}
                onChange={set('password')}
                placeholder="Minimum 8 characters"
                error={errors.password}
              />
              <Input
                label="Confirm Password"
                type="password"
                value={form.confirmPassword}
                onChange={set('confirmPassword')}
                placeholder="Repeat password"
                error={errors.confirmPassword}
              />

              <Alert variant="info">After registration, sign in to view policies already assigned to your account.</Alert>

              {submitError && <Alert variant="error">{submitError}</Alert>}

              <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
                {isSubmitting ? 'Creating account…' : 'Create Account'}
              </Button>
            </form>

            <p className="text-center text-sm text-gray-500 mt-6">
              Already have an account?{' '}
              <button onClick={onGoSignIn} className="text-axa-blue font-semibold hover:underline">Sign in</button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
