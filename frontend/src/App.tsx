import { useState } from 'react';
import type { AppState, Role, Screen } from './types';
import { Layout } from './components/Layout';

// Auth
import LandingPage from './screens/auth/LandingPage';
import SignUpPage from './screens/auth/SignUpPage';
import PolicyVerification from './screens/auth/PolicyVerification';
import type { Policy } from './types';

// Customer
import CustomerHome from './screens/customer/CustomerHome';
import MyPolicies from './screens/customer/MyPolicies';
import PolicyDetails from './screens/customer/PolicyDetails';
import MyClaims from './screens/customer/MyClaims';
import NewClaim from './screens/customer/NewClaim';
import ClaimProcessing from './screens/customer/ClaimProcessing';
import ClaimDetails from './screens/customer/ClaimDetails';
import Profile from './screens/customer/Profile';

// Assessor
import AssessorQueue from './screens/assessor/AssessorQueue';
import AssessorClaims from './screens/assessor/AssessorClaims';
import AssessorReview from './screens/assessor/AssessorReview';

// Operations
import OperationsOverview from './screens/operations/OperationsOverview';

const INITIAL_STATE: AppState = {
  screen: 'landing',
  role: null,
};

export default function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_STATE);
  const [token, setToken] = useState<string | null>(null);
  const [signup, setSignup] = useState<{ account: { fullName: string; email: string; password: string; nationalId: string }; policies: Policy[] } | null>(null);

  const navigate = (screen: Screen, params: Record<string, string> = {}) => {
    setAppState(prev => ({
      ...prev,
      screen,
      ...(params.selectedPolicyId !== undefined ? { selectedPolicyId: params.selectedPolicyId } : {}),
      ...(params.selectedClaimId !== undefined ? { selectedClaimId: params.selectedClaimId } : {}),
      ...(params.selectedAssessorClaimId !== undefined
        ? { selectedAssessorClaimId: params.selectedAssessorClaimId }
        : {}),
      ...(params.processingDocuments !== undefined ? { processingDocuments: params.processingDocuments } : {}),
      ...(params.completedExtractions !== undefined ? { completedExtractions: params.completedExtractions } : {}),
      ...(params.processingFailures !== undefined ? { processingFailures: params.processingFailures } : {}),
      ...(params.processingValidationResults !== undefined ? { processingValidationResults: params.processingValidationResults } : {}),
    }));
  };

  const signIn = (session: { access_token: string; user: { user_id: string; full_name: string; email: string; role: string } }) => {
    const role = session.user.role.toLowerCase() as Role;
    const homeScreen: Screen = role === 'customer' ? 'customer-home' : role === 'assessor' ? 'assessor-queue' : 'operations';
    localStorage.setItem('axa_access_token', session.access_token);
    setToken(session.access_token);
    setAppState({ screen: homeScreen, role, userId: session.user.user_id, userName: session.user.full_name, userEmail: session.user.email });
  };

  const signOut = () => { localStorage.removeItem('axa_access_token'); setToken(null); setAppState(INITIAL_STATE); };

  const { screen, role, userName, userEmail, selectedPolicyId, selectedClaimId, selectedAssessorClaimId, processingDocuments, completedExtractions, processingFailures, processingValidationResults } =
    appState;

  // ── Auth screens (no layout) ────────────────────────────────────────────────
  if (!role) {
    if (screen === 'signup') {
      return (
        <SignUpPage
          onPoliciesVerified={(account, policies) => {
            setSignup({ account, policies });
            navigate('policy-verification');
          }}
          onGoSignIn={() => navigate('landing')}
        />
      );
    }
    if (screen === 'policy-verification' && signup) {
      return (
        <PolicyVerification
          account={signup.account}
          policies={signup.policies}
          onComplete={() => setSignup(null)}
          onGoSignIn={() => navigate('landing')}
        />
      );
    }
    return <LandingPage onSignIn={signIn} onGoSignUp={() => navigate('signup')} />;
  }

  // ── Claim processing (full screen, no sidebar) ──────────────────────────────
  if (screen === 'claim-processing') {
    return <ClaimProcessing
      claimId={selectedClaimId || ''}
      documentsProcessed={Number(processingDocuments || 0)}
      extractionsCompleted={Number(completedExtractions || 0)}
      processingFailures={Number(processingFailures || 0)}
      validationResults={processingValidationResults || '[]'}
      token={token || ''}
      navigate={navigate}
    />;
  }

  // ── Authenticated screens (with layout) ────────────────────────────────────
  return (
    <Layout
      role={role}
      userName={userName || ''}
      currentScreen={screen}
      navigate={navigate}
      onSignOut={signOut}
    >
      {/* Customer screens */}
      {role === 'customer' && (
        <>
          {screen === 'customer-home' && (
            <CustomerHome userName={userName || 'Customer'} token={token || ''} navigate={navigate} />
          )}
          {screen === 'my-policies' && <MyPolicies navigate={navigate} token={token || ''} />}
          {screen === 'policy-details' && (
            <PolicyDetails policyId={selectedPolicyId || ''} token={token || ''} navigate={navigate} />
          )}
          {screen === 'my-claims' && <MyClaims navigate={navigate} token={token || ''} />}
          {screen === 'new-claim' && (
            <NewClaim preselectedPolicyId={selectedPolicyId} token={token || ''} navigate={navigate} />
          )}
          {screen === 'claim-details' && (
            <ClaimDetails claimId={selectedClaimId || ''} token={token || ''} initialValidationResults={processingValidationResults || '[]'} navigate={navigate} />
          )}
          {screen === 'profile' && <Profile userName={userName || 'Customer'} userEmail={userEmail || ''} token={token || ''} />}
        </>
      )}

      {/* Assessor screens */}
      {role === 'assessor' && (
        <>
          {screen === 'assessor-queue' && <AssessorQueue token={token || ''} navigate={navigate} />}
          {screen === 'assessor-claims' && <AssessorClaims token={token || ''} navigate={navigate} />}
          {screen === 'assessor-review' && (
            <AssessorReview
              claimId={selectedAssessorClaimId || 'clm-004'}
              token={token || ''}
              navigate={navigate}
            />
          )}
        </>
      )}

      {/* Operations screen */}
      {role === 'operations' && <OperationsOverview token={token || ''} />}
    </Layout>
  );
}
