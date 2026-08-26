import { useEffect, useRef, useState } from 'react';
import { Alert, Amount, Button, Card, DocStatusChip, Input, PageHeader, PolicyStatusBadge, ProductBadge, Select, Textarea } from '../../components/UI';
import { createClaim, extractClaimDocument, getMyPolicies, uploadClaimDocument } from '../../api';
import type { DocumentValidation } from '../../api';
import type { Policy, Screen } from '../../types';

interface NewClaimProps { preselectedPolicyId?: string; token: string; navigate: (screen: Screen, params?: Record<string, string>) => void; }

const STEPS = ['Select Policy', 'Claim Details', 'Upload Documents', 'Confirm'];
const CLAIM_TYPES: Record<string, string[]> = {
  HEALTH: ['Inpatient Hospitalisation', 'Day-Case Surgery', 'Diagnostics', 'Medication', 'Emergency Treatment', 'Outpatient Consultation', 'Maternity', 'Dental'],
  MOTOR: ['Collision', 'Fire', 'Theft', 'Third-Party', 'Windscreen / Glass'],
  PROPERTY: ['Fire', 'Lightning', 'Explosion', 'Accidental Damage', 'Theft', 'Burst Internal Pipe', 'Flood'],
  TRAVEL: ['Emergency Medical', 'Trip Cancellation', 'Baggage Loss', 'Baggage Delay', 'Travel Document Replacement'],
};
// Mirrors the existing backend checklist only to select files before a claim exists.
const REQUIRED_DOCUMENTS: Record<string, Record<string, string[]>> = {
  HEALTH: { 'Inpatient Hospitalisation': ['Medical Report', 'Itemised Hospital Invoice', 'Member ID'], 'Day-Case Surgery': ['Medical Report', 'Itemised Hospital Invoice', 'Member ID'], Diagnostics: ['Referring Physician Request', 'Itemised Invoice', 'Member ID'], Medication: ['Prescription', 'Pharmacy Invoice', 'Member ID'], 'Emergency Treatment': ['Medical Report', 'Itemised Invoice', 'Member ID'], 'Outpatient Consultation': ['Medical Report', 'Member ID'], Maternity: ['Medical Report', 'Itemised Hospital Invoice', 'Member ID'], Dental: ['Medical Report', 'Itemised Invoice', 'Member ID'] },
  MOTOR: { Collision: ['Photos of Damage', 'Repair Estimate', "Driver's Licence", 'Vehicle Registration'], Fire: ['Photos of Damage', 'Fire Brigade Report', 'Vehicle Registration'], Theft: ['Police Theft Report', "Driver's Licence", 'Vehicle Registration', 'Spare Key'], 'Third-Party': ['Police Report', 'Photos of Damage', 'Repair Estimate', "Driver's Licence", 'Vehicle Registration'], 'Windscreen / Glass': ['Photos of Damage', 'Repair Estimate', 'Vehicle Registration'] },
  PROPERTY: { Fire: ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'], Lightning: ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'], Explosion: ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'], 'Accidental Damage': ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'], Theft: ['Police Report (Forced Entry)', 'Itemised List', 'Proof of Ownership'], 'Burst Internal Pipe': ['Photos of Damage', 'Plumber Report', 'Itemised List'], Flood: ['Photos of Damage', 'Itemised List', 'Repair / Replacement Quotations'] },
  TRAVEL: { 'Emergency Medical': ['Physician Report', 'Itemised Invoices'], 'Trip Cancellation': ['Proof of Covered Reason'], 'Baggage Loss': ['Airline PIR or Police Report', 'Receipts / Proof of Ownership'], 'Baggage Delay': ['Airline Property Irregularity Report', 'Receipts for Essentials'], 'Travel Document Replacement': ['Police Report', 'Embassy / Consulate Statement'] },
};

export default function NewClaim({ preselectedPolicyId, token, navigate }: NewClaimProps) {
  const [step, setStep] = useState(preselectedPolicyId ? 1 : 0);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState(preselectedPolicyId || '');
  const [claimType, setClaimType] = useState('');
  const [incidentDate, setIncidentDate] = useState('');
  const [claimedAmount, setClaimedAmount] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState<Record<string, File>>({});
  const [pendingDocumentType, setPendingDocumentType] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadError, setLoadError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    getMyPolicies(token).then(ownedPolicies => {
      setPolicies(ownedPolicies);
      if (preselectedPolicyId && !ownedPolicies.some(policy => policy.id === preselectedPolicyId)) {
        setLoadError('The selected policy is no longer available in your account.');
        setSelectedPolicyId('');
        setStep(0);
      }
    }).catch(error => setLoadError(error instanceof Error ? error.message : 'Unable to load your policies.'));
  }, [preselectedPolicyId, token]);
  const policy = policies.find(item => item.id === selectedPolicyId);
  const requiredDocuments = policy && claimType ? REQUIRED_DOCUMENTS[policy.productLine]?.[claimType] || [] : [];
  const missingDocuments = requiredDocuments.filter(documentType => !files[documentType]);
  const validateDetails = () => {
    const nextErrors: Record<string, string> = {};
    if (!claimType) nextErrors.claimType = 'Please select a claim type.';
    if (!incidentDate) nextErrors.incidentDate = 'Incident date is required.';
    if (!claimedAmount || Number.isNaN(Number(claimedAmount)) || Number(claimedAmount) < 0) nextErrors.claimedAmount = 'Enter a valid claim amount.';
    if (description.trim().length < 20) nextErrors.description = 'Please provide at least 20 characters describing what happened.';
    setErrors(nextErrors); return Object.keys(nextErrors).length === 0;
  };
  const selectDocument = (event: React.ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; if (file && pendingDocumentType) setFiles(current => ({ ...current, [pendingDocumentType]: file })); setPendingDocumentType(''); event.target.value = ''; };
  const submitClaim = async () => {
    if (!policy) return;
    setSubmitting(true); setLoadError('');
    try {
      const claim = await createClaim(token, { policyId: policy.id, claimType, incidentDate, claimedAmount: Number(claimedAmount), description: description.trim() });
      let processed = 0; let extracted = 0; let failures = 0;
      const validationResults: { documentType: string; validation: DocumentValidation }[] = [];
      for (const document of claim.required_documents) {
        const file = files[document.document_type]; if (!file) continue;
        try {
          const uploaded = await uploadClaimDocument(token, claim.claim_id, document.document_type, file);
          processed += 1;
          const extraction = await extractClaimDocument(token, claim.claim_id, uploaded.document_id);
          validationResults.push({ documentType: document.document_type, validation: extraction.validation });
          extracted += 1;
        } catch {
          failures += 1;
          validationResults.push({ documentType: document.document_type, validation: { status: 'failed', document_valid: false, message: 'We could not process this document. Please upload a clear, supported file and try again.', errors: [], warnings: [], expected_document_type: document.document_type, detected_document_type: null } });
        }
      }
      navigate('claim-processing', { selectedClaimId: claim.claim_id, processingDocuments: String(processed), completedExtractions: String(extracted), processingFailures: String(failures), processingValidationResults: JSON.stringify(validationResults) });
    } catch (error) { setLoadError(error instanceof Error ? error.message : 'Unable to submit your claim.'); setSubmitting(false); }
  };

  return <div className="animate-fade-in">
    <input ref={fileRef} type="file" className="hidden" onChange={selectDocument} />
    <PageHeader title="New Claim" back={{ label: 'My Claims', onClick: () => navigate('my-claims') }} />
    <div className="flex items-center mb-8">{STEPS.map((label, index) => <div key={label} className="flex items-center flex-1 last:flex-none"><div className={`flex items-center gap-2 ${index <= step ? 'text-axa-blue' : 'text-gray-400'}`}><div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${index < step ? 'bg-emerald-500 text-white' : index === step ? 'bg-axa-blue text-white' : 'border-2 border-gray-300 text-gray-400'}`}>{index < step ? '✓' : index + 1}</div><span className="text-xs font-medium hidden sm:block">{label}</span></div>{index < STEPS.length - 1 && <div className={`flex-1 h-px mx-3 ${index < step ? 'bg-emerald-400' : 'bg-gray-200'}`} />}</div>)}</div>
    {loadError && <Alert variant="error" className="mb-5">{loadError}</Alert>}
    {step === 0 && <div className="space-y-4"><div className="bg-white border border-gray-200 rounded-xl p-5"><h2 className="text-base font-semibold text-gray-900 mb-1">Select Policy</h2><p className="text-sm text-gray-500">Choose one of your active policies for this claim.</p></div><div className="space-y-3">{policies.map(item => <button type="button" key={item.id} disabled={item.status !== 'ACTIVE'} onClick={() => { setSelectedPolicyId(item.id); setClaimType(''); setFiles({}); }} className={`w-full text-left border-2 rounded-xl p-4 ${item.status !== 'ACTIVE' ? 'opacity-60 cursor-not-allowed border-gray-200' : item.id === selectedPolicyId ? 'border-axa-blue bg-axa-blue-50' : 'border-gray-200 hover:border-gray-300'}`}><div className="flex gap-3"><div><div className="flex gap-2 mb-1"><ProductBadge line={item.productLine} /><PolicyStatusBadge status={item.status} /></div><p className="font-mono text-sm font-semibold text-gray-800">{item.number}</p><p className="text-xs text-gray-500 mt-2">Remaining: <Amount value={item.remainingLimit} size="sm" /></p></div></div></button>)}</div><div className="flex justify-end pt-4"><Button onClick={() => selectedPolicyId && setStep(1)} disabled={!selectedPolicyId} size="lg">Continue →</Button></div></div>}
    {step === 1 && policy && <div className="space-y-5"><Card className="p-4 border-axa-blue-100"><div className="flex items-center gap-3"><ProductBadge line={policy.productLine} /><span className="font-mono text-sm font-semibold text-gray-800">{policy.number}</span><PolicyStatusBadge status={policy.status} /></div></Card><div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4"><h2 className="text-base font-semibold text-gray-900">Claim Details</h2><Select label="Claim Type" value={claimType} onChange={event => { setClaimType(event.target.value); setFiles({}); }} error={errors.claimType}><option value="">Select claim type…</option>{(CLAIM_TYPES[policy.productLine] || []).map(type => <option key={type} value={type}>{type}</option>)}</Select><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><Input label="Incident Date" type="date" value={incidentDate} onChange={event => setIncidentDate(event.target.value)} max={new Date().toISOString().split('T')[0]} error={errors.incidentDate} /><Input label="Claim Amount (EGP)" type="number" value={claimedAmount} onChange={event => setClaimedAmount(event.target.value)} min="0" error={errors.claimedAmount} /></div><Textarea label="Describe what happened" value={description} onChange={event => setDescription(event.target.value)} rows={5} error={errors.description} hint="Minimum 20 characters." /></div><div className="flex justify-between"><Button variant="outline" onClick={() => setStep(0)}>← Back</Button><Button onClick={() => validateDetails() && setStep(2)} size="lg">Continue →</Button></div></div>}
    {step === 2 && policy && <div className="space-y-5"><Alert variant="info" title="Upload documents">Choose files now. They are uploaded only after you confirm and submit the claim.</Alert><Card className="p-5"><h2 className="text-base font-semibold text-gray-900">Required Documents</h2><div className="space-y-3 mt-5">{requiredDocuments.map(documentType => <div key={documentType} className="flex items-center justify-between gap-3 border border-gray-200 rounded-lg p-3"><div className="min-w-0"><p className="text-sm font-semibold text-gray-800">{documentType}</p><p className="text-xs text-gray-500 truncate">{files[documentType]?.name || 'Required'}</p></div><div className="flex items-center gap-3"><DocStatusChip status={files[documentType] ? 'UPLOADED' : 'MISSING'} /><Button size="sm" variant="outline" onClick={() => { setPendingDocumentType(documentType); fileRef.current?.click(); }}>{files[documentType] ? 'Replace' : 'Choose file'}</Button></div></div>)}</div></Card><div className="flex justify-between"><Button variant="outline" onClick={() => setStep(1)}>← Back</Button><Button onClick={() => setStep(3)} size="lg">Review claim →</Button></div></div>}
    {step === 3 && policy && <div className="space-y-5"><Card className="p-5"><h2 className="text-base font-semibold text-gray-900 mb-3">Claim Summary</h2><div className="space-y-2 text-sm"><p><span className="text-gray-500">Policy:</span> <span className="font-mono font-semibold">{policy.number}</span></p><p><span className="text-gray-500">Claim type:</span> {claimType}</p><p><span className="text-gray-500">Incident date:</span> {incidentDate}</p><p><span className="text-gray-500">Claimed amount:</span> <Amount value={Number(claimedAmount)} size="sm" /></p><p><span className="text-gray-500">Description:</span> {description}</p></div></Card><Card className="p-5"><h2 className="text-base font-semibold text-gray-900">Uploaded Documents</h2><div className="mt-3 space-y-2">{requiredDocuments.filter(documentType => files[documentType]).map(documentType => <div key={documentType} className="flex justify-between text-sm"><span>{documentType}</span><span className="text-gray-500">{files[documentType].name}</span></div>)}{Object.keys(files).length === 0 && <p className="text-sm text-gray-500">No documents selected.</p>}</div></Card>{missingDocuments.length > 0 && <Alert variant="warning" title="Missing required documents">{missingDocuments.join(', ')}. The claim will remain waiting for documents until these are uploaded.</Alert>}<Alert variant="info">No human review has been requested. Policy validation, coverage checks, risk checks, and decisions are not performed in this step.</Alert><div className="flex justify-between"><Button variant="outline" onClick={() => setStep(2)}>← Back</Button><Button onClick={submitClaim} loading={submitting} size="lg">Submit Claim</Button></div></div>}
  </div>;
}
