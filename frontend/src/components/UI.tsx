import type { ProductLine, ClaimStatus, PolicyStatus, RiskLevel } from '../types';

// ─── Status Badge ─────────────────────────────────────────────────────────────

const CLAIM_STATUS_CONFIG: Record<ClaimStatus, { label: string; bg: string; text: string; dot: string }> = {
  PROCESSING: { label: 'Processing', bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  WAITING_FOR_DOCUMENTS: { label: 'Docs Required', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  UNDER_HUMAN_REVIEW: { label: 'Human Review', bg: 'bg-violet-50', text: 'text-violet-700', dot: 'bg-violet-500' },
  APPROVED: { label: 'Approved', bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  REJECTED: { label: 'Rejected', bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
  ROUTED: { label: 'Routed', bg: 'bg-indigo-50', text: 'text-indigo-700', dot: 'bg-indigo-500' },
  ESCALATED: { label: 'Escalated', bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500' },
  BELOW_DEDUCTIBLE: { label: 'Below Deductible', bg: 'bg-gray-100', text: 'text-gray-600', dot: 'bg-gray-400' },
  CLOSED: { label: 'Closed', bg: 'bg-gray-100', text: 'text-gray-600', dot: 'bg-gray-400' },
};

const POLICY_STATUS_CONFIG: Record<PolicyStatus, { label: string; bg: string; text: string }> = {
  ACTIVE: { label: 'Active', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  LAPSED: { label: 'Lapsed', bg: 'bg-amber-50', text: 'text-amber-700' },
  CANCELLED: { label: 'Cancelled', bg: 'bg-red-50', text: 'text-red-700' },
  PENDING: { label: 'Pending', bg: 'bg-blue-50', text: 'text-blue-700' },
};

export function ClaimStatusBadge({ status }: { status: ClaimStatus }) {
  const c = CLAIM_STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

export function PolicyStatusBadge({ status }: { status: PolicyStatus }) {
  const c = POLICY_STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

const RISK_CONFIG: Record<RiskLevel, { label: string; bg: string; text: string }> = {
  HIGH: { label: 'High Risk', bg: 'bg-red-50', text: 'text-red-700' },
  MEDIUM: { label: 'Medium Risk', bg: 'bg-amber-50', text: 'text-amber-700' },
  LOW: { label: 'Low Risk', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  NONE: { label: 'No Risk', bg: 'bg-gray-100', text: 'text-gray-600' },
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  const c = RISK_CONFIG[level];
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

// ─── Product Line Badge ────────────────────────────────────────────────────────

const PRODUCT_CONFIG: Record<ProductLine, { label: string; bg: string; text: string; icon: string }> = {
  HEALTH: { label: 'Health', bg: 'bg-emerald-50', text: 'text-emerald-700', icon: '🏥' },
  MOTOR: { label: 'Motor', bg: 'bg-blue-50', text: 'text-blue-700', icon: '🚗' },
  PROPERTY: { label: 'Property', bg: 'bg-amber-50', text: 'text-amber-700', icon: '🏠' },
  TRAVEL: { label: 'Travel', bg: 'bg-violet-50', text: 'text-violet-700', icon: '✈️' },
};

export function ProductBadge({ line }: { line: ProductLine }) {
  const c = PRODUCT_CONFIG[line];
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span>{c.icon}</span>
      {c.label}
    </span>
  );
}

export function ProductLineAccent({ line }: { line: ProductLine }) {
  const c = PRODUCT_CONFIG[line];
  return <span className={`font-semibold ${c.text}`}>{c.label}</span>;
}

export function getProductConfig(line: ProductLine) {
  return PRODUCT_CONFIG[line];
}

// ─── Document Status ───────────────────────────────────────────────────────────

export function DocStatusChip({ status }: { status: 'MISSING' | 'UPLOADED' | 'VERIFIED' }) {
  if (status === 'VERIFIED')
    return <span className="text-xs font-medium text-emerald-600 flex items-center gap-1"><span>✓</span> Verified</span>;
  if (status === 'UPLOADED')
    return <span className="text-xs font-medium text-blue-600 flex items-center gap-1"><span>↑</span> Uploaded</span>;
  return <span className="text-xs font-medium text-amber-600 flex items-center gap-1"><span>!</span> Missing</span>;
}

// ─── Button ────────────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
type ButtonSize = 'sm' | 'md' | 'lg';

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-axa-blue text-white hover:bg-axa-blue-dark shadow-sm',
  secondary: 'bg-axa-blue-100 text-axa-blue hover:bg-blue-100',
  danger: 'bg-red-600 text-white hover:bg-red-700 shadow-sm',
  ghost: 'text-gray-600 hover:bg-gray-100',
  outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50 bg-white',
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-2.5 text-sm',
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export function Button({ variant = 'primary', size = 'md', loading, children, className = '', disabled, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-axa-blue focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
    >
      {loading && <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin-slow" />}
      {children}
    </button>
  );
}

// ─── Input ─────────────────────────────────────────────────────────────────────

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({ label, error, hint, className = '', id, ...props }: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="flex flex-col gap-1">
      {label && <label htmlFor={inputId} className="text-sm font-medium text-gray-700">{label}</label>}
      <input
        id={inputId}
        {...props}
        className={`w-full px-3 py-2 text-sm border rounded-lg bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-axa-blue focus:border-transparent transition-colors ${error ? 'border-red-400' : 'border-gray-300'} ${className}`}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

// ─── Textarea ──────────────────────────────────────────────────────────────────

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Textarea({ label, error, hint, className = '', id, ...props }: TextareaProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="flex flex-col gap-1">
      {label && <label htmlFor={inputId} className="text-sm font-medium text-gray-700">{label}</label>}
      <textarea
        id={inputId}
        {...props}
        className={`w-full px-3 py-2 text-sm border rounded-lg bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-axa-blue focus:border-transparent transition-colors resize-none ${error ? 'border-red-400' : 'border-gray-300'} ${className}`}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

// ─── Select ────────────────────────────────────────────────────────────────────

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Select({ label, error, hint, className = '', id, children, ...props }: SelectProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="flex flex-col gap-1">
      {label && <label htmlFor={inputId} className="text-sm font-medium text-gray-700">{label}</label>}
      <select
        id={inputId}
        {...props}
        className={`w-full px-3 py-2 text-sm border rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-axa-blue focus:border-transparent transition-colors ${error ? 'border-red-400' : 'border-gray-300'} ${className}`}
      >
        {children}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  );
}

// ─── Card ──────────────────────────────────────────────────────────────────────

export function Card({ children, className = '', onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white border border-gray-200 rounded-xl shadow-sm ${onClick ? 'cursor-pointer hover:border-axa-blue hover:shadow-md transition-all' : ''} ${className}`}
    >
      {children}
    </div>
  );
}

// ─── Section Header ────────────────────────────────────────────────────────────

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// ─── Alert ─────────────────────────────────────────────────────────────────────

type AlertVariant = 'info' | 'success' | 'warning' | 'error';

const ALERT_STYLES: Record<AlertVariant, string> = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  error: 'bg-red-50 border-red-200 text-red-800',
};

const ALERT_ICONS: Record<AlertVariant, string> = {
  info: 'ℹ',
  success: '✓',
  warning: '⚠',
  error: '✕',
};

export function Alert({ variant = 'info', title, children, className = '' }: { variant?: AlertVariant; title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`flex gap-3 p-4 rounded-lg border ${ALERT_STYLES[variant]} ${className}`}>
      <span className="text-base leading-none mt-0.5">{ALERT_ICONS[variant]}</span>
      <div className="flex-1 min-w-0">
        {title && <p className="text-sm font-semibold mb-0.5">{title}</p>}
        <div className="text-sm">{children}</div>
      </div>
    </div>
  );
}

// ─── Empty State ───────────────────────────────────────────────────────────────

export function EmptyState({ icon, title, description, action }: { icon: string; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-base font-semibold text-gray-900 mb-1">{title}</h3>
      {description && <p className="text-sm text-gray-500 max-w-xs mb-6">{description}</p>}
      {action}
    </div>
  );
}

// ─── Spinner ───────────────────────────────────────────────────────────────────

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const s = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-8 h-8' : 'w-6 h-6';
  return <span className={`${s} border-2 border-axa-blue border-t-transparent rounded-full animate-spin-slow inline-block`} />;
}

// ─── Tab Bar ───────────────────────────────────────────────────────────────────

export function TabBar({ tabs, active, onChange }: { tabs: string[]; active: string; onChange: (t: string) => void }) {
  return (
    <div className="flex border-b border-gray-200 mb-5">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            active === t
              ? 'border-axa-blue text-axa-blue'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  );
}

// ─── Data Row ──────────────────────────────────────────────────────────────────

export function DataRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex justify-between items-baseline py-2.5 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500 shrink-0">{label}</span>
      <span className={`text-sm text-gray-900 font-medium text-right ml-4 ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  );
}

// ─── Loading Screen ────────────────────────────────────────────────────────────

export function LoadingScreen({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-64 gap-4">
      <Spinner size="lg" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}

// ─── Amount Display ────────────────────────────────────────────────────────────

export function Amount({ value, size = 'base' }: { value: number; size?: 'sm' | 'base' | 'lg' | 'xl' }) {
  const formatted = new Intl.NumberFormat('en-EG', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
  const sizeClass = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg' : size === 'xl' ? 'text-2xl' : 'text-base';
  return (
    <span className={`font-mono font-semibold ${sizeClass}`}>
      EGP {formatted}
    </span>
  );
}

// ─── Progress Bar ──────────────────────────────────────────────────────────────

export function ProgressBar({ value, max, colorClass = 'bg-axa-blue' }: { value: number; max: number; colorClass?: string }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all ${colorClass}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ─── Section Divider ───────────────────────────────────────────────────────────

export function Divider({ label }: { label?: string }) {
  if (!label) return <hr className="border-gray-200 my-4" />;
  return (
    <div className="flex items-center gap-3 my-4">
      <hr className="flex-1 border-gray-200" />
      <span className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</span>
      <hr className="flex-1 border-gray-200" />
    </div>
  );
}

// ─── Breadcrumb ───────────────────────────────────────────────────────────────

export function Breadcrumb({ items }: { items: { label: string; onClick?: () => void }[] }) {
  return (
    <nav className="flex items-center gap-1.5 text-sm text-gray-500 mb-4">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-gray-300">/</span>}
          {item.onClick ? (
            <button onClick={item.onClick} className="hover:text-axa-blue transition-colors">{item.label}</button>
          ) : (
            <span className={i === items.length - 1 ? 'text-gray-900 font-medium' : ''}>{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

// ─── AXA Logo ─────────────────────────────────────────────────────────────────

export function AxaLogo({ size = 'md', light = false }: { size?: 'sm' | 'md' | 'lg'; light?: boolean }) {
  const s = size === 'sm' ? 'text-xl' : size === 'lg' ? 'text-4xl' : 'text-2xl';
  return (
    <div className="flex items-center gap-2">
      <div className={`font-black tracking-tight ${s} ${light ? 'text-white' : 'text-axa-blue'}`} style={{ fontFamily: 'var(--font-display)' }}>
        AXA
      </div>
      <div className={`text-xs font-semibold tracking-widest uppercase ${light ? 'text-white/70' : 'text-gray-500'} ${size === 'sm' ? 'text-[10px]' : ''}`}>
        Egypt
      </div>
    </div>
  );
}

// ─── Page Header ──────────────────────────────────────────────────────────────

export function PageHeader({ title, subtitle, back, action }: {
  title: string;
  subtitle?: string;
  back?: { label: string; onClick: () => void };
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6">
      {back && (
        <button
          onClick={back.onClick}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-axa-blue mb-3 transition-colors"
        >
          <span>←</span>
          {back.label}
        </button>
      )}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>{title}</h1>
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
    </div>
  );
}
