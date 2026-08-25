import { useState } from 'react';
import type { AppState, Screen, Role } from './types';
import { Layout } from './components/Layout';

// Auth
import LandingPage from './screens/auth/LandingPage';
import SignUpPage from './screens/auth/SignUpPage';
import PolicyVerification from './screens/auth/PolicyVerification';

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
  const [signUpData, setSignUpData] = useState<{
    fullName: string;
    email: string;
    nationalId: string;
  } | null>(null);

  const navigate = (screen: Screen, params: Record<string, string> = {}) => {
    setAppState(prev => ({
      ...prev,
      screen,
      ...(params.selectedPolicyId !== undefined ? { selectedPolicyId: params.selectedPolicyId } : {}),
      ...(params.selectedClaimId !== undefined ? { selectedClaimId: params.selectedClaimId } : {}),
      ...(params.selectedAssessorClaimId !== undefined
        ? { selectedAssessorClaimId: params.selectedAssessorClaimId }
        : {}),
    }));
  };

  const signIn = (role: Role, name: string) => {
    const homeScreen: Screen =
      role === 'customer' ? 'customer-home' : role === 'assessor' ? 'assessor-queue' : 'operations';
    setAppState({ screen: homeScreen, role, userName: name });
  };

  const signOut = () => setAppState(INITIAL_STATE);

  const { screen, role, userName, selectedPolicyId, selectedClaimId, selectedAssessorClaimId } =
    appState;

  // ── Auth screens (no layout) ────────────────────────────────────────────────
  if (!role) {
    if (screen === 'signup') {
      return (
        <SignUpPage
          onNext={data => {
            setSignUpData(data);
            navigate('policy-verification');
          }}
          onGoSignIn={() => navigate('landing')}
        />
      );
    }
    if (screen === 'policy-verification' && signUpData) {
      return (
        <PolicyVerification
          userName={signUpData.fullName}
          nationalId={signUpData.nationalId}
          onComplete={() => signIn('customer', signUpData.fullName)}
        />
      );
    }
    return <LandingPage onSignIn={signIn} onGoSignUp={() => navigate('signup')} />;
  }

  // ── Claim processing (full screen, no sidebar) ──────────────────────────────
  if (screen === 'claim-processing') {
    return <ClaimProcessing navigate={navigate} />;
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
            <CustomerHome userName={userName || 'Customer'} navigate={navigate} />
          )}
          {screen === 'my-policies' && <MyPolicies navigate={navigate} />}
          {screen === 'policy-details' && (
            <PolicyDetails policyId={selectedPolicyId || ''} navigate={navigate} />
          )}
          {screen === 'my-claims' && <MyClaims navigate={navigate} />}
          {screen === 'new-claim' && (
            <NewClaim preselectedPolicyId={selectedPolicyId} navigate={navigate} />
          )}
          {screen === 'claim-details' && (
            <ClaimDetails claimId={selectedClaimId || 'clm-001'} navigate={navigate} />
          )}
          {screen === 'profile' && <Profile userName={userName || 'Customer'} />}
        </>
      )}

      {/* Assessor screens */}
      {role === 'assessor' && (
        <>
          {screen === 'assessor-queue' && <AssessorQueue navigate={navigate} />}
          {screen === 'assessor-claims' && <AssessorClaims navigate={navigate} />}
          {screen === 'assessor-review' && (
            <AssessorReview
              claimId={selectedAssessorClaimId || 'clm-004'}
              navigate={navigate}
            />
          )}
        </>
      )}

      {/* Operations screen */}
      {role === 'operations' && <OperationsOverview />}
    </Layout>
  );
}
