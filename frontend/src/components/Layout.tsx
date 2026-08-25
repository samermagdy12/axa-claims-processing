import { AxaLogo } from './UI';
import type { Screen, Role } from '../types';

interface NavItem {
  label: string;
  screen: Screen;
  icon: string;
}

const CUSTOMER_NAV: NavItem[] = [
  { label: 'Home', screen: 'customer-home', icon: '⊞' },
  { label: 'My Policies', screen: 'my-policies', icon: '🗂' },
  { label: 'My Claims', screen: 'my-claims', icon: '📋' },
  { label: 'New Claim', screen: 'new-claim', icon: '＋' },
  { label: 'Profile', screen: 'profile', icon: '👤' },
];

const ASSESSOR_NAV: NavItem[] = [
  { label: 'Review Queue', screen: 'assessor-queue', icon: '⊞' },
  { label: 'Claims', screen: 'assessor-claims', icon: '📋' },
  { label: 'Claim Review', screen: 'assessor-review', icon: '🔍' },
];

const OPERATIONS_NAV: NavItem[] = [
  { label: 'Operations Overview', screen: 'operations', icon: '📊' },
];

const NAV_MAP: Record<Role, NavItem[]> = {
  customer: CUSTOMER_NAV,
  assessor: ASSESSOR_NAV,
  operations: OPERATIONS_NAV,
};

const ROLE_LABEL: Record<Role, { label: string; color: string; bg: string }> = {
  customer: { label: 'Customer', color: 'text-axa-blue', bg: 'bg-axa-blue-50' },
  assessor: { label: 'Assessor', color: 'text-violet-700', bg: 'bg-violet-50' },
  operations: { label: 'Operations', color: 'text-gray-600', bg: 'bg-gray-100' },
};

interface LayoutProps {
  children: React.ReactNode;
  role: Role;
  userName: string;
  currentScreen: Screen;
  navigate: (screen: Screen) => void;
  onSignOut: () => void;
}

export function Layout({ children, role, userName, currentScreen, navigate, onSignOut }: LayoutProps) {
  const navItems = NAV_MAP[role];
  const roleInfo = ROLE_LABEL[role];

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-axa-blue flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/10">
          <AxaLogo light />
          <p className="text-white/50 text-[10px] mt-1 tracking-wider uppercase">Claims Platform</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {navItems.map((item) => {
            const isActive = currentScreen === item.screen ||
              (item.screen === 'assessor-queue' && currentScreen === 'assessor-review') ||
              (item.screen === 'assessor-review' && currentScreen === 'assessor-review');
            return (
              <button
                key={item.screen}
                onClick={() => navigate(item.screen)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-left ${
                  isActive
                    ? 'bg-white text-axa-blue shadow-sm'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                <span className="text-base leading-none w-5 text-center">{item.icon}</span>
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* User info */}
        <div className="px-4 py-4 border-t border-white/10">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              {userName.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-white text-xs font-semibold truncate">{userName}</p>
              <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${roleInfo.bg} ${roleInfo.color}`}>
                {roleInfo.label}
              </span>
            </div>
          </div>
          <button
            onClick={onSignOut}
            className="w-full text-left text-xs text-white/50 hover:text-white/80 transition-colors"
          >
            Sign out →
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-6">
          {children}
        </div>
      </main>
    </div>
  );
}
