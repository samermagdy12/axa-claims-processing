import { useState, useRef } from 'react';
import { Button, Input, Textarea, Select, Card, ProductBadge, PolicyStatusBadge, Alert, Amount, PageHeader, DocStatusChip } from '../../components/UI';
import { CUSTOMER_POLICIES, CLAIM_TYPES, REQUIRED_DOCUMENTS } from '../../data';
import type { Screen, Policy } from '../../types';

interface NewClaimProps {
  preselectedPolicyId?: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

interface DocUpload {
  name: string;
  status: 'MISSING' | 'UPLOADING' | 'UPLOADED';
  fileName?: string;
}

const STEPS = ['Select Policy', 'Claim Details', 'Upload Documents', 'Confirm'];

export default function NewClaim({ preselectedPolicyId, navigate }: NewClaimProps) {
  const [step, setStep] = useState(preselectedPolicyId ? 1 : 0);
  const [selectedPolicyId, setSelectedPolicyId] = useState(preselectedPolicyId || '');
  const [claimType, setClaimType] = useState('');
  const [incidentDate, setIncidentDate] = useState('');
  const [claimedAmount, setClaimedAmount] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [docs, setDocs] = useState<DocUpload[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const policy = CUSTOMER_POLICIES.find(p => p.id === selectedPolicyId);
  const activePolicies = CUSTOMER_POLICIES.filter(p => p.status === 'ACTIVE');

  const claimTypes = policy ? CLAIM_TYPES[policy.productLine] || [] : [];

  const handlePolicySelect = (id: string) => {
    setSelectedPolicyId(id);
    setClaimType('');
    setDocs([]);
  };

  const handleClaimTypeChange = (type: string) => {
    setClaimType(type);
    if (policy) {
      const required = REQUIRED_DOCUMENTS[policy.productLine]?.[type] || [];
      setDocs(required.map(name => ({ name, status: 'MISSING' })));
    }
  };

  const validateStep1 = () => {
    if (!selectedPolicyId) { setErrors({ policy: 'Please select a policy.' }); return false; }
    setErrors({});
    return true;
  };

  const validateStep2 = () => {
    const e: Record<string, string> = {};
    if (!claimType) e.claimType = 'Please select a claim type.';
    if (!incidentDate) e.incidentDate = 'Incident date is required.';
    if (!claimedAmount || isNaN(Number(claimedAmount)) || Number(claimedAmount) <= 0)
      e.claimedAmount = 'Enter a valid claim amount.';
    if (!description.trim() || description.trim().length < 20)
      e.description = 'Please provide at least 20 characters describing what happened.';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleFileUpload = (docName: string, file: File) => {
    setDocs(prev => prev.map(d =>
      d.name === docName ? { ...d, status: 'UPLOADING', fileName: file.name } : d
    ));
    setTimeout(() => {
      setDocs(prev => prev.map(d =>
        d.name === docName ? { ...d, status: 'UPLOADED' } : d
      ));
    }, 1000 + Math.random() * 1000);
  };

  const handleRemoveDoc = (docName: string) => {
    setDocs(prev => prev.map(d =>
      d.name === docName ? { ...d, status: 'MISSING', fileName: undefined } : d
    ));
  };

  const handleSubmit = () => {
    setSubmitting(true);
    setTimeout(() => navigate('claim-processing'), 800);
  };

  const nextStep = () => {
    if (step === 0 && !validateStep1()) return;
    if (step === 1 && !validateStep2()) return;
    setStep(s => s + 1);
  };

  const prevStep = () => setStep(s => Math.max(0, s - 1));

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="New Claim"
        back={{ label: 'My Claims', onClick: () => navigate('my-claims') }}
      />

      {/* Stepper */}
      <div className="flex items-center mb-8">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center flex-1 last:flex-none">
            <div className={`flex items-center gap-2 ${i <= step ? 'text-axa-blue' : 'text-gray-400'}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                i < step ? 'bg-emerald-500 text-white' : i === step ? 'bg-axa-blue text-white' : 'border-2 border-gray-300 text-gray-400'
              }`}>
                {i < step ? '✓' : i + 1}
              </div>
              <span className="text-xs font-medium hidden sm:block">{label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-3 transition-colors ${i < step ? 'bg-emerald-400' : 'bg-gray-200'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step 0: Policy Selection */}
      {step === 0 && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5 mb-5">
            <h2 className="text-base font-semibold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>Select Policy</h2>
            <p className="text-sm text-gray-500">Choose the policy this claim is against. You can only claim against your own active policies.</p>
          </div>

          {errors.policy && <Alert variant="error">{errors.policy}</Alert>}

          {activePolicies.length === 0 && (
            <Alert variant="warning" title="No active policies">
              You have no active policies. Activate or renew a policy before submitting a claim.
            </Alert>
          )}

          <div className="space-y-3">
            {CUSTOMER_POLICIES.map(p => {
              const isActive = p.status === 'ACTIVE';
              const isSelected = p.id === selectedPolicyId;
              return (
                <div
                  key={p.id}
                  onClick={() => isActive && handlePolicySelect(p.id)}
                  className={`border-2 rounded-xl p-4 transition-all ${
                    !isActive ? 'opacity-60 cursor-not-allowed border-gray-200' :
                    isSelected ? 'border-axa-blue bg-axa-blue-50 cursor-pointer' :
                    'border-gray-200 hover:border-gray-300 cursor-pointer'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-5 h-5 rounded-full border-2 mt-0.5 flex-shrink-0 flex items-center justify-center transition-colors ${
                      isSelected ? 'border-axa-blue bg-axa-blue' : 'border-gray-300'
                    }`}>
                      {isSelected && <span className="w-2 h-2 bg-white rounded-full" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <ProductBadge line={p.productLine} />
                        <PolicyStatusBadge status={p.status} />
                        {!isActive && <span className="text-xs text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">Not available for claims</span>}
                      </div>
                      <p className="font-mono text-sm font-semibold text-gray-800">{p.number}</p>
                      <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                        <span>Remaining: <strong className="text-gray-800"><Amount value={p.remainingLimit} size="sm" /></strong></span>
                        <span>Deductible: <strong className="text-gray-800">EGP {p.deductible.toLocaleString()}</strong></span>
                        <span>{p.startDate} → {p.endDate}</span>
                      </div>
                      {p.riders.length > 0 && (
                        <div className="flex gap-1.5 mt-2">
                          {p.riders.map(r => <span key={r} className="text-xs bg-axa-blue-50 text-axa-blue px-2 py-0.5 rounded-full">{r}</span>)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex justify-end pt-4">
            <Button onClick={nextStep} disabled={!selectedPolicyId} size="lg">
              Continue →
            </Button>
          </div>
        </div>
      )}

      {/* Step 1: Claim details */}
      {step === 1 && policy && (
        <div className="space-y-5">
          {/* Selected policy summary */}
          <Card className="p-4 border-axa-blue-100">
            <div className="flex items-center gap-3">
              <ProductBadge line={policy.productLine} />
              <span className="font-mono text-sm font-semibold text-gray-800">{policy.number}</span>
              <PolicyStatusBadge status={policy.status} />
              <span className="ml-auto text-xs text-gray-500">
                Remaining: <Amount value={policy.remainingLimit} size="sm" />
              </span>
            </div>
          </Card>

          {Number(claimedAmount) > 10000 && (
            <Alert variant="info" title="Amount above auto-approval cap">
              Claims above EGP 10,000 cannot be automatically approved (Clause 0.2f). Your claim will be routed to a human assessor.
            </Alert>
          )}

          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Claim Details</h2>

            <Select
              label="Claim Type"
              value={claimType}
              onChange={e => handleClaimTypeChange(e.target.value)}
              error={errors.claimType}
            >
              <option value="">Select claim type…</option>
              {claimTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </Select>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Incident Date"
                type="date"
                value={incidentDate}
                onChange={e => setIncidentDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                error={errors.incidentDate}
              />
              <Input
                label="Claim Amount (EGP)"
                type="number"
                value={claimedAmount}
                onChange={e => setClaimedAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                error={errors.claimedAmount}
              />
            </div>

            <Textarea
              label="Describe what happened"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Provide a clear description of the incident — what happened, when, where, and any relevant details that support your claim. The more detail you provide, the faster we can process your claim."
              rows={5}
              error={errors.description}
              hint="Minimum 20 characters. Your description will be used to verify your claim — it does not override policy rules or this handbook."
            />

            {description.length > 0 && description.length < 20 && (
              <p className="text-xs text-gray-400">{description.length}/20 characters minimum</p>
            )}
          </div>

          {claimType && (
            <Alert variant="info" title="Required documents for this claim type">
              <ul className="mt-1 space-y-0.5">
                {(REQUIRED_DOCUMENTS[policy.productLine]?.[claimType] || []).map(d => (
                  <li key={d}>· {d}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs">You will upload these on the next screen.</p>
            </Alert>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={prevStep}>← Back</Button>
            <Button onClick={nextStep} size="lg">Continue →</Button>
          </div>
        </div>
      )}

      {/* Step 2: Document upload */}
      {step === 2 && (
        <div className="space-y-5">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>Upload Required Documents</h2>
            <p className="text-sm text-gray-500">
              The following documents are required for a <strong>{claimType}</strong> claim. All required documents must be uploaded before submitting.
            </p>
          </div>

          {docs.length === 0 ? (
            <Alert variant="warning">No document requirements found. Please go back and select a valid claim type.</Alert>
          ) : (
            <div className="space-y-3">
              {docs.map((doc) => (
                <Card key={doc.name} className="p-4">
                  <div className="flex items-center gap-4">
                    {/* Status icon */}
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      doc.status === 'UPLOADED' ? 'bg-emerald-100' :
                      doc.status === 'UPLOADING' ? 'bg-blue-100' : 'bg-amber-50'
                    }`}>
                      {doc.status === 'UPLOADED' ? '✅' : doc.status === 'UPLOADING' ? '⏳' : '📄'}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-gray-800">{doc.name}</p>
                        <span className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded font-medium">Required</span>
                        <DocStatusChip status={doc.status === 'UPLOADING' ? 'UPLOADED' : doc.status} />
                      </div>
                      {doc.fileName && doc.status !== 'MISSING' && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate">📎 {doc.fileName}</p>
                      )}
                      {doc.status === 'UPLOADING' && (
                        <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: '60%', transition: 'width 1s' }} />
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      {doc.status === 'UPLOADED' && (
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveDoc(doc.name)}>
                          Remove
                        </Button>
                      )}
                      <input
                        type="file"
                        ref={el => { fileRefs.current[doc.name] = el; }}
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png,.zip"
                        onChange={e => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(doc.name, file);
                        }}
                      />
                      <Button
                        variant={doc.status === 'UPLOADED' ? 'outline' : 'primary'}
                        size="sm"
                        onClick={() => fileRefs.current[doc.name]?.click()}
                        loading={doc.status === 'UPLOADING'}
                        disabled={doc.status === 'UPLOADING'}
                      >
                        {doc.status === 'UPLOADED' ? 'Replace' : 'Upload'}
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Progress summary */}
          {docs.length > 0 && (
            <div className="bg-gray-50 rounded-xl p-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">
                  {docs.filter(d => d.status === 'UPLOADED').length} of {docs.length} documents uploaded
                </span>
                <span className={`font-semibold ${
                  docs.every(d => d.status === 'UPLOADED') ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {docs.every(d => d.status === 'UPLOADED') ? 'Ready to submit ✓' : 'Missing documents'}
                </span>
              </div>
            </div>
          )}

          {docs.some(d => d.status === 'MISSING') && (
            <Alert variant="warning" title="Missing documents">
              You can still proceed with missing documents, but your claim will be placed on hold until all required documents are uploaded. You will receive a list of missing documents and can upload them later.
            </Alert>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={prevStep}>← Back</Button>
            <Button
              onClick={nextStep}
              size="lg"
              disabled={docs.some(d => d.status === 'UPLOADING')}
            >
              Review & Submit →
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Confirmation */}
      {step === 3 && policy && (
        <div className="space-y-5">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-1" style={{ fontFamily: 'var(--font-display)' }}>Review & Confirm</h2>
            <p className="text-sm text-gray-500">Please review your claim details before submitting. Once submitted, you cannot edit your claim.</p>
          </div>

          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Claim Summary</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Policy</span>
                <div className="flex items-center gap-2">
                  <ProductBadge line={policy.productLine} />
                  <span className="font-mono text-sm font-semibold">{policy.number}</span>
                </div>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Claim type</span>
                <span className="text-sm font-semibold">{claimType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Incident date</span>
                <span className="text-sm font-semibold">{incidentDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Claimed amount</span>
                <Amount value={Number(claimedAmount)} />
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Description</p>
              <p className="text-sm text-gray-800 leading-relaxed">{description}</p>
            </div>
          </Card>

          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Uploaded Documents ({docs.filter(d => d.status === 'UPLOADED').length}/{docs.length})
            </h3>
            <div className="space-y-2">
              {docs.map(doc => (
                <div key={doc.name} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">
                    {doc.status === 'UPLOADED' ? '✅' : '⚠️'} {doc.name}
                  </span>
                  <div className="flex items-center gap-2">
                    {doc.fileName && <span className="text-xs text-gray-400">{doc.fileName}</span>}
                    <DocStatusChip status={doc.status === 'UPLOADING' ? 'UPLOADED' : doc.status} />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {Number(claimedAmount) > 10000 && (
            <Alert variant="info" title="Claim will be routed to human review">
              This claim exceeds EGP 10,000 and cannot be automatically approved (Clause 0.3). An AXA assessor will review it.
            </Alert>
          )}

          {docs.some(d => d.status === 'MISSING') && (
            <Alert variant="warning" title="Missing documents">
              Your claim will be placed on hold until all required documents are received. You can upload missing documents from the claim details screen.
            </Alert>
          )}

          <Alert variant="info">
            By submitting, you confirm that all information is accurate and complete. Your claim narrative is informational — it does not override policy rules or the AXA Claims Handbook.
          </Alert>

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={prevStep}>← Edit Claim</Button>
            <Button onClick={handleSubmit} loading={submitting} size="lg">
              Submit Claim
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
