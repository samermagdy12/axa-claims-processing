import { useState } from 'react';
import { Button, Input, Alert } from '../../components/UI';
import type { Role } from '../../types';
import { login } from '../../api';

interface LandingPageProps {
  onSignIn: (session: { access_token: string; user: { user_id: string; full_name: string; email: string; role: string } }) => void;
  onGoSignUp: () => void;
}

const DEMO_ROLES: {
  role: Role;
  name: string;
  email: string;
  title: string;
  desc: string;
  icon: string;
  active: string;
  inactive: string;
}[] = [
  {
    role: 'customer',
    name: 'Ahmed Hassan',
    email: 'ahmed.hassan@email.com',
    title: 'Customer',
    desc: 'Manage policies · File & track claims',
    icon: '👤',
    active: 'border-axa-blue bg-axa-blue text-white',
    inactive: 'border-gray-200 bg-white text-gray-700 hover:border-axa-blue',
  },
  {
    role: 'assessor',
    name: 'Sara Khalil',
    email: 'sara.khalil@axa-egypt.com',
    title: 'Assessor',
    desc: 'Review queue · Human decisions',
    icon: '🔍',
    active: 'border-violet-500 bg-violet-600 text-white',
    inactive: 'border-gray-200 bg-white text-gray-700 hover:border-violet-400',
  },
  {
    role: 'operations',
    name: 'Hany Ibrahim',
    email: 'hany.ibrahim@axa-egypt.com',
    title: 'Operations',
    desc: 'Read-only processing summary',
    icon: '📊',
    active: 'border-gray-600 bg-gray-700 text-white',
    inactive: 'border-gray-200 bg-white text-gray-700 hover:border-gray-400',
  },
];

export default function LandingPage({ onSignIn, onGoSignUp }: LandingPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [selectedRole, setSelectedRole] = useState<Role>('customer');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRoleSelect = (r: typeof DEMO_ROLES[0]) => {
    setSelectedRole(r.role);
    setEmail(r.email);
    setPassword('demo');
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) { setError('Please enter your password.'); return; }
    setError('');
    setIsSubmitting(true);
    try { onSignIn(await login({ email, password })); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Unable to sign in.'); }
    finally { setIsSubmitting(false); }
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Left panel — brand */}
      <div className="hidden lg:flex w-[52%] bg-axa-blue relative overflow-hidden flex-col">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full bg-white/5" />
          <div className="absolute top-1/3 -right-48 w-[600px] h-[600px] rounded-full bg-axa-red/10" />
          <div className="absolute -bottom-20 left-1/4 w-80 h-80 rounded-full bg-white/5" />
          {/* Grid pattern */}
          <div
            className="absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: 'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
              backgroundSize: '40px 40px',
            }}
          />
        </div>

        <div className="relative flex flex-col justify-between h-full p-12">
          {/* Logo */}
          <div>
            <div className="font-black text-5xl tracking-tight text-white" style={{ fontFamily: 'var(--font-display)' }}>
              AXA
            </div>
            <div className="text-white/50 text-xs font-semibold tracking-[4px] uppercase mt-1">Egypt</div>
          </div>

          {/* Headline */}
          <div>
            <h1 className="text-white text-4xl font-bold leading-tight mb-5" style={{ fontFamily: 'var(--font-display)' }}>
              AI-Powered<br />Claims Processing
            </h1>
            <p className="text-white/65 text-base leading-relaxed max-w-sm">
              Transparent, policy-grounded decisions across Health, Motor, Property, and Travel — every outcome traceable to a handbook clause.
            </p>

            <div className="mt-10 grid grid-cols-2 gap-3">
              {[
                { icon: '🏥', label: 'Health' },
                { icon: '🚗', label: 'Motor' },
                { icon: '🏠', label: 'Property' },
                { icon: '✈️', label: 'Travel' },
              ].map(({ icon, label }) => (
                <div key={label} className="flex items-center gap-2.5 bg-white/8 rounded-xl px-4 py-3">
                  <span className="text-xl">{icon}</span>
                  <span className="text-white/80 text-sm font-medium">{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Feature bullets */}
          <div className="space-y-3">
            {[
              { icon: '⚡', text: 'Auto-approval up to EGP 10,000 — no waiting' },
              { icon: '📋', text: 'Dynamic document requirements per claim type' },
              { icon: '🔍', text: 'Every decision cited to the AXA Claims Handbook' },
              { icon: '🛡', text: 'Fraud-risk detection before auto-approval' },
            ].map(({ icon, text }) => (
              <div key={text} className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center text-sm flex-shrink-0">{icon}</span>
                <span className="text-white/65 text-sm">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — sign in */}
      <div className="flex-1 flex flex-col justify-center px-8 lg:px-14 py-10 bg-white">
        <div className="max-w-md w-full mx-auto">
          {/* Mobile logo */}
          <div className="lg:hidden mb-8 flex items-center gap-3">
            <div className="font-black text-2xl text-axa-blue" style={{ fontFamily: 'var(--font-display)' }}>AXA</div>
            <span className="text-xs font-semibold text-gray-400 tracking-wider uppercase">Egypt Claims</span>
          </div>

          <div className="mb-7">
            <h2 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Sign in</h2>
            <p className="text-sm text-gray-500 mt-1">Access your claims platform account.</p>
          </div>

          {/* The backend, not this form, resolves the authenticated user's role. */}
          {false && (<div className="mb-6">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Select demo role</p>
            <div className="grid grid-cols-3 gap-2">
              {DEMO_ROLES.map(r => (
                <button
                  key={r.role}
                  onClick={() => handleRoleSelect(r)}
                  className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border-2 text-center transition-all ${
                    selectedRole === r.role ? r.active : r.inactive
                  }`}
                >
                  <span className="text-xl">{r.icon}</span>
                  <span className="text-xs font-bold leading-tight">{r.title}</span>
                  <span className={`text-[10px] leading-tight ${selectedRole === r.role ? 'opacity-80' : 'text-gray-400'}`}>
                    {r.desc.split('·')[0].trim()}
                  </span>
                </button>
              ))}
            </div>
          </div>)}
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email address"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
            <div>
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError(''); }}
                placeholder="Enter your password"
              />
            </div>

            {error && <Alert variant="error">{error}</Alert>}

            <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
              Sign In →
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-500">
              New customer?{' '}
              <button onClick={onGoSignUp} className="text-axa-blue font-semibold hover:underline">
                Create account
              </button>
            </p>
          </div>

          {/* Product line badges at bottom */}
          <div className="mt-8 flex flex-wrap justify-center gap-2">
            {[
              { label: 'Health', color: 'bg-emerald-50 text-emerald-700' },
              { label: 'Motor', color: 'bg-blue-50 text-blue-700' },
              { label: 'Property', color: 'bg-amber-50 text-amber-700' },
              { label: 'Travel', color: 'bg-violet-50 text-violet-700' },
            ].map(({ label, color }) => (
              <span key={label} className={`text-xs font-semibold px-2.5 py-1 rounded-full ${color}`}>{label}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
