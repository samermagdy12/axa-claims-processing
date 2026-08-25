import { useEffect, useState } from 'react';
import { Button, Input, Textarea, Select, Card, ProductBadge, PolicyStatusBadge, Alert, Amount, PageHeader, DocStatusChip } from '../../components/UI';
import { createClaim, getMyPolicies, type CreatedClaim } from '../../api';
import type { Policy, Screen } from '../../types';

interface NewClaimProps {
  preselectedPolicyId?: string;
  token: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

const STEPS = ['Select Policy', 'Claim Details', 'Required Documents'];

const CLAIM_TYPES: Record<string, string[]> = {
  HEALTH: ['Inpatient Hospitalisation', 'Day-Case Surgery', 'Diagnostics', 'Medication', 'Emergency Treatment', 'Outpatient Consultation', 'Maternity', 'Dental'],
  MOTOR: ['Collision', 'Fire', 'Theft', 'Third-Party', 'Windscreen / Glass'],
  PROPERTY: ['Fire', 'Lightning', 'Explosion', 'Accidental Damage', 'Theft', 'Burst Internal Pipe', 'Flood'],
  TRAVEL: ['Emergency Medical', 'Trip Cancellation', 'Baggage Loss', 'Baggage Delay', 'Travel Document Replacement'],
};

export default function NewClaim({ preselectedPolicyId, token, navigate }: NewClaimProps) {
  const [step, setStep] = useState(preselectedPolicyId ? 1 : 0);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState(preselectedPolicyId || '');
  const [claimType, setClaimType] = useState('');
  const [incidentDate, setIncidentDate] = useState('');
  const [claimedAmount, setClaimedAmount] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadError, setLoadError] = useState('');
  const [createdClaim, setCreatedClaim] = useState<CreatedClaim | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getMyPolicies(token)
      .then(ownedPolicies => {
        setPolicies(ownedPolicies);
        if (preselectedPolicyId && !ownedPolicies.some(policy => policy.id === preselectedPolicyId)) {
          setLoadError('The selected policy is no longer available in your account.');
          setStep(0);
          setSelectedPolicyId('');
        }
      })
      .catch(error => setLoadError(error instanceof Error ? error.message : 'Unable to load your policies.'));
  }, [preselectedPolicyId, token]);

  const policy = policies.find(item => item.id === selectedPolicyId);
  const activePolicies = policies.filter(item => item.status === 'ACTIVE');

  const handlePolicySelect = (policyId: string) => {
    setSelectedPolicyId(policyId);
    setClaimType('');
    setErrors({});
  };

  const validateDetails = () => {
    const nextErrors: Record<string, string> = {};
    if (!claimType) nextErrors.claimType = 'Please select a claim type.';
    if (!incidentDate) nextErrors.incidentDate = 'Incident date is required.';
    if (!claimedAmount || Number.isNaN(Number(claimedAmount)) || Number(claimedAmount) < 0) nextErrors.claimedAmount = 'Enter a valid claim amount.';
    if (description.trim().length < 20) nextErrors.description = 'Please provide at least 20 characters describing what happened.';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const submitClaim = async () => {
    if (!policy || !validateDetails()) return;
    setSubmitting(true);
    setLoadError('');
    try {
      const claim = await createClaim(token, { policyId: policy.id, claimType, incidentDate, claimedAmount: Number(claimedAmount), description: description.trim() });
      setCreatedClaim(claim);
      setStep(2);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Unable to create your claim.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <PageHeader title="New Claim" back={{ label: 'My Claims', onClick: () => navigate('my-claims') }} />
      <div className="flex items-center mb-8">
        {STEPS.map((label, index) => <div key={label} className="flex items-center flex-1 last:flex-none"><div className={`flex items-center gap-2 ${index <= step ? 'text-axa-blue' : 'text-gray-400'}`}><div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${index < step ? 'bg-emerald-500 text-white' : index === step ? 'bg-axa-blue text-white' : 'border-2 border-gray-300 text-gray-400'}`}>{index < step ? '✓' : index + 1}</div><span className="text-xs font-medium hidden sm:block">{label}</span></div>{index < STEPS.length - 1 && <div className={`flex-1 h-px mx-3 ${index < step ? 'bg-emerald-400' : 'bg-gray-200'}`} />}</div>)}
      </div>
      {loadError && <Alert variant="error" className="mb-5">{loadError}</Alert>}

      {step === 0 && <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5"><h2 className="text-base font-semibold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>Select Policy</h2><p className="text-sm text-gray-500">Choose one of your active policies for this claim.</p></div>
        {activePolicies.length === 0 && <Alert variant="warning" title="No active policies">You have no active policies available for a new claim.</Alert>}
        <div className="space-y-3">{policies.map(item => {
          const isActive = item.status === 'ACTIVE';
          const isSelected = item.id === selectedPolicyId;
          return <button type="button" key={item.id} disabled={!isActive} onClick={() => handlePolicySelect(item.id)} className={`w-full text-left border-2 rounded-xl p-4 ${!isActive ? 'opacity-60 cursor-not-allowed border-gray-200' : isSelected ? 'border-axa-blue bg-axa-blue-50' : 'border-gray-200 hover:border-gray-300'}`}><div className="flex items-start gap-3"><div className={`w-5 h-5 rounded-full border-2 mt-0.5 flex-shrink-0 ${isSelected ? 'border-axa-blue bg-axa-blue' : 'border-gray-300'}`}>{isSelected && <span className="block w-2 h-2 bg-white rounded-full m-0.5" />}</div><div><div className="flex gap-2 mb-1"><ProductBadge line={item.productLine} /><PolicyStatusBadge status={item.status} /></div><p className="font-mono text-sm font-semibold text-gray-800">{item.number}</p><p className="text-xs text-gray-500 mt-2">Remaining: <Amount value={item.remainingLimit} size="sm" /> · {item.startDate} → {item.endDate}</p></div></div></button>;
        })}</div>
        <div className="flex justify-end pt-4"><Button onClick={() => selectedPolicyId && setStep(1)} disabled={!selectedPolicyId} size="lg">Continue →</Button></div>
      </div>}

      {step === 1 && policy && <div className="space-y-5">
        <Card className="p-4 border-axa-blue-100"><div className="flex items-center gap-3"><ProductBadge line={policy.productLine} /><span className="font-mono text-sm font-semibold text-gray-800">{policy.number}</span><PolicyStatusBadge status={policy.status} /><span className="ml-auto text-xs text-gray-500">Remaining: <Amount value={policy.remainingLimit} size="sm" /></span></div></Card>
        <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4"><h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Claim Details</h2><Select label="Claim Type" value={claimType} onChange={event => setClaimType(event.target.value)} error={errors.claimType}><option value="">Select claim type…</option>{(CLAIM_TYPES[policy.productLine] || []).map(type => <option key={type} value={type}>{type}</option>)}</Select><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><Input label="Incident Date" type="date" value={incidentDate} onChange={event => setIncidentDate(event.target.value)} max={new Date().toISOString().split('T')[0]} error={errors.incidentDate} /><Input label="Claim Amount (EGP)" type="number" value={claimedAmount} onChange={event => setClaimedAmount(event.target.value)} placeholder="0.00" min="0" error={errors.claimedAmount} /></div><Textarea label="Describe what happened" value={description} onChange={event => setDescription(event.target.value)} rows={5} error={errors.description} hint="Minimum 20 characters. Your description does not override policy rules or the handbook." /></div>
        <div className="flex justify-between pt-2"><Button variant="outline" onClick={() => setStep(0)}>← Back</Button><Button onClick={submitClaim} loading={submitting} size="lg">Create Claim →</Button></div>
      </div>}

      {step === 2 && createdClaim && <div className="space-y-5">
        <Alert variant="success" title="Claim created">Your claim has been created and is waiting for the required documents.</Alert>
        <Card className="p-5"><h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Required Documents</h2><p className="text-sm text-gray-500 mt-1">Claim reference: <span className="font-mono">{createdClaim.claim_id}</span></p><div className="space-y-3 mt-5">{createdClaim.required_documents.map(document => <div key={document.claim_required_document_id} className="flex items-center justify-between border border-gray-200 rounded-lg p-3"><div><p className="text-sm font-semibold text-gray-800">{document.document_type}</p><p className="text-xs text-red-600 mt-1">Required</p></div><DocStatusChip status={document.status} /></div>)}</div></Card>
        <Alert variant="info">Document upload is the next claim-processing phase. This checklist is saved with your claim and shows exactly what is still missing.</Alert>
        <div className="flex justify-end"><Button onClick={() => navigate('my-claims', { selectedClaimId: createdClaim.claim_id })}>View My Claims</Button></div>
      </div>}
    </div>
  );
}
