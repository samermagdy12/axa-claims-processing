import { useEffect, useRef, useState } from 'react';
import {
  Button, Card, ClaimStatusBadge, ProductBadge, PageHeader, Amount, Alert, DataRow, DocStatusChip, Spinner,
} from '../../components/UI';
import { extractClaimDocument, getClaim, removeClaimDocument, uploadClaimDocument } from '../../api';
import type { DocumentValidation } from '../../api';
import type { Claim, Screen } from '../../types';

interface ClaimDetailsProps {
  claimId: string;
  token: string;
  initialValidationResults: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function ClaimDetails({ claimId, token, initialValidationResults, navigate }: ClaimDetailsProps) {
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadingDocument, setUploadingDocument] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState('');
  const [pendingDocumentType, setPendingDocumentType] = useState('');
  const [documentValidation, setDocumentValidation] = useState<Record<string, DocumentValidation>>(() => parseValidationResults(initialValidationResults));
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    getClaim(claimId, token)
      .then(nextClaim => { if (active) setClaim(nextClaim); })
      .catch(requestError => { if (active) setError(requestError instanceof Error ? requestError.message : 'Unable to load this claim.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [claimId, token]);

  if (loading) return <div className="p-6 text-gray-500">Loading claim...</div>;
  if (!claim) return (
    <div className="p-6">
      <Alert variant="error">{error || 'Claim not found.'}</Alert>
      <Button variant="ghost" onClick={() => navigate('my-claims')} className="mt-3">← Back</Button>
    </div>
  );

  const chooseDocument = (documentType: string) => {
    setUploadError('');
    setPendingDocumentType(documentType);
    fileRef.current?.click();
  };

  const uploadSelectedDocument = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !pendingDocumentType) return;
    setUploadingDocument(pendingDocumentType);
    setUploadError('');
    try {
      const uploaded = await uploadClaimDocument(token, claim.id, pendingDocumentType, file);
      setDocumentValidation(current => ({ ...current, [pendingDocumentType]: pendingValidation(pendingDocumentType) }));
      const extraction = await extractClaimDocument(token, claim.id, uploaded.document_id);
      setDocumentValidation(current => ({ ...current, [pendingDocumentType]: extraction.validation }));
      setClaim(await getClaim(claim.id, token));
    } catch (requestError) {
      const message = 'We could not process this document. Please upload a clear, supported file and try again.';
      setDocumentValidation(current => ({ ...current, [pendingDocumentType]: failedValidation(pendingDocumentType, message) }));
      setUploadError(message);
    } finally {
      setUploadingDocument(null);
      setPendingDocumentType('');
      event.target.value = '';
    }
  };

  const replaceDocument = async (documentType: string) => {
    setUploadingDocument(documentType);
    setUploadError('');
    try {
      await removeClaimDocument(token, claim.id, documentType);
      setDocumentValidation(current => {
        const next = { ...current };
        delete next[documentType];
        return next;
      });
      setClaim(await getClaim(claim.id, token));
      setPendingDocumentType(documentType);
      fileRef.current?.click();
    } catch {
      setUploadError('Unable to replace this document right now. Please try again.');
    } finally {
      setUploadingDocument(null);
    }
  };

  return (
    <div className="animate-fade-in">
      <input ref={fileRef} type="file" className="hidden" onChange={uploadSelectedDocument} />
      <PageHeader
        title={`Claim ${claim.id.toUpperCase()}`}
        subtitle={`${claim.claimType} · Submitted ${claim.submissionDate}`}
        back={{ label: 'My Claims', onClick: () => navigate('my-claims') }}
        action={<ClaimStatusBadge status={claim.status} />}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-5">
          {/* Status panel */}
          <StatusPanel claim={claim} />

          {/* Claim details */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Claim Information</h3>
            <DataRow label="Claim ID" value={<span className="font-mono text-xs">{claim.id.toUpperCase()}</span>} />
            <DataRow label="Policy" value={<span className="font-mono text-xs">{claim.policyNumber}</span>} />
            <DataRow label="Product line" value={<ProductBadge line={claim.productLine} />} />
            <DataRow label="Claim type" value={claim.claimType} />
            <DataRow label="Incident date" value={claim.incidentDate} />
            <DataRow label="Submission date" value={claim.submissionDate} />
            <DataRow label="Claimed amount" value={<Amount value={claim.claimedAmount} />} />
            <DataRow label="Status" value={<ClaimStatusBadge status={claim.status} />} />
          </Card>

          {/* Description */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-2" style={{ fontFamily: 'var(--font-display)' }}>Your Description</h3>
            <p className="text-sm text-gray-700 leading-relaxed">{claim.description}</p>
            <p className="text-xs text-gray-400 mt-3">
              This description is informational. It does not override policy rules or the AXA Claims Handbook.
            </p>
          </Card>

          {/* Documents */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Documents</h3>
            {uploadError && <Alert variant="error" className="mb-3">{uploadError}</Alert>}
            <div className="space-y-2">
              {claim.documents.map(doc => {
                const effectiveStatus = doc.status;
                const validation = documentValidation[doc.type];
                return (
                  <div key={doc.type} className={`p-3 rounded-lg border ${
                    validation?.status === 'valid' ? 'border-emerald-200 bg-emerald-50' :
                    validation?.status === 'invalid' || validation?.status === 'failed' ? 'border-red-200 bg-red-50' :
                    validation?.status === 'warning' ? 'border-amber-200 bg-amber-50' :
                    doc.status === 'VERIFIED' ? 'border-emerald-200 bg-emerald-50' :
                    doc.status === 'UPLOADED' ? 'border-blue-200 bg-blue-50' :
                    'border-amber-200 bg-amber-50'
                  }`}>
                    <div className="flex items-center gap-3">
                    <div className="text-lg flex-shrink-0">
                      {validation?.status === 'valid' ? '✅' : validation?.status === 'invalid' || validation?.status === 'failed' ? '❌' : effectiveStatus === 'VERIFIED' ? '✅' : effectiveStatus === 'UPLOADED' ? '📄' : '📋'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-800">{doc.type}</p>
                      {doc.fileName && <p className="text-xs text-gray-500 truncate">📎 {doc.fileName}</p>}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {uploadingDocument === doc.type && <Spinner size="sm" />}
                      <DocStatusChip status={doc.status} />
                      {doc.status === 'MISSING' && uploadingDocument !== doc.type && (
                        <Button size="sm" onClick={() => chooseDocument(doc.type)}>Upload</Button>
                      )}
                      {(validation?.status === 'invalid' || validation?.status === 'failed') && uploadingDocument !== doc.type && (
                        <Button size="sm" variant="outline" onClick={() => replaceDocument(doc.type)}>Replace</Button>
                      )}
                    </div>
                    </div>
                    {validation && <DocumentValidationNotice validation={validation} />}
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {/* Decision */}
          {claim.decision && <DecisionCard claim={claim} />}

          {/* Handbook clause */}
          {claim.decision?.handbookClause && (
            <Card className="p-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Handbook Reference</p>
              <p className="text-sm font-mono font-semibold text-axa-blue">{claim.decision.handbookClause}</p>
            </Card>
          )}

          {/* Quick actions */}
          <Card className="p-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Actions</p>
            <div className="space-y-2">
              <p className="text-xs text-gray-500 pb-1">Your claim progresses automatically once required documents have been validated.</p>
              <Button variant="outline" className="w-full" onClick={() => navigate('my-claims')}>
                ← All Claims
              </Button>
              <Button variant="outline" className="w-full" onClick={() => navigate('new-claim')}>
                + New Claim
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function pendingValidation(expectedDocumentType: string): DocumentValidation {
  return { status: 'pending', document_valid: null, message: 'Processing your document. This may take a moment.', errors: [], warnings: [], expected_document_type: expectedDocumentType, detected_document_type: null };
}

function parseValidationResults(value: string): Record<string, DocumentValidation> {
  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) return {};
    return Object.fromEntries(parsed.filter(item => item && typeof item.documentType === 'string' && item.validation).map(item => [item.documentType, item.validation]));
  } catch {
    return {};
  }
}

function failedValidation(expectedDocumentType: string, message: string): DocumentValidation {
  return { status: 'failed', document_valid: false, message, errors: [], warnings: [], expected_document_type: expectedDocumentType, detected_document_type: null };
}

function DocumentValidationNotice({ validation }: { validation: DocumentValidation }) {
  const color = validation.status === 'valid' ? 'text-emerald-800' : validation.status === 'invalid' || validation.status === 'failed' ? 'text-red-800' : validation.status === 'pending' ? 'text-blue-800' : 'text-amber-800';
  return <div className={`mt-2 ml-8 text-xs ${color}`}>
    <p className="font-semibold">{validation.message}</p>
    {validation.status === 'invalid' && <div className="mt-1 space-y-0.5">{validation.errors.map(error => <p key={error}>{error}</p>)}<p>Please upload the correct document.</p></div>}
    {validation.status === 'warning' && validation.warnings.map(warning => <p className="mt-1" key={warning}>{warning}</p>)}
    {validation.status === 'failed' && <p className="mt-1">You can try again with a clearer file.</p>}
  </div>;
}

function StatusPanel({ claim }: { claim: Claim }) {
  if (claim.status === 'APPROVED') {
    return (
      <div className="bg-emerald-600 rounded-2xl p-6 text-white">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">✓</div>
          <div>
            <h3 className="text-lg font-bold mb-0.5" style={{ fontFamily: 'var(--font-display)' }}>Claim Approved</h3>
            {claim.decision?.approvedAmount && (
              <div className="flex items-baseline gap-1">
                <Amount value={claim.decision.approvedAmount} size="xl" />
                <span className="text-white/70 text-sm">approved</span>
              </div>
            )}
            {claim.decision?.deductible && (
              <p className="text-white/70 text-xs mt-0.5">
                EGP {claim.claimedAmount.toLocaleString()} − EGP {claim.decision.deductible.toLocaleString()} deductible
              </p>
            )}
            {claim.decision?.customerMessage && (
              <p className="text-white/80 text-sm mt-3 leading-relaxed">{claim.decision.customerMessage}</p>
            )}
            {claim.decision?.handbookClause && (
              <p className="text-white/50 text-xs mt-2">Reference: {claim.decision.handbookClause}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (claim.status === 'REJECTED') {
    return (
      <div className="bg-red-600 rounded-2xl p-6 text-white">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">✕</div>
          <div>
            <h3 className="text-lg font-bold mb-0.5" style={{ fontFamily: 'var(--font-display)' }}>Claim Rejected</h3>
            {claim.decision?.reason && <p className="text-white/80 text-sm mt-1">{claim.decision.reason}</p>}
            {claim.decision?.handbookClause && (
              <p className="text-white/60 text-xs mt-2">Handbook reference: {claim.decision.handbookClause}</p>
            )}
            {claim.decision?.customerMessage && (
              <p className="text-white/70 text-sm mt-3">{claim.decision.customerMessage}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (claim.status === 'WAITING_FOR_DOCUMENTS') {
    const missingDocs = claim.documents.filter(d => d.status === 'MISSING');

    if (missingDocs.length === 0) {
      return (
        <div className="bg-blue-600 rounded-2xl p-6 text-white">
          <h3 className="font-bold text-lg">Documents Received</h3>
          <p className="text-white/80 text-sm mt-1">All documents uploaded. Your claim is being reprocessed.</p>
        </div>
      );
    }

    return (
      <div className="border-2 border-amber-400 bg-amber-50 rounded-2xl p-5">
        <div className="flex gap-3">
          <span className="text-2xl">⚠️</span>
          <div className="flex-1">
            <h3 className="font-bold text-amber-900 text-base" style={{ fontFamily: 'var(--font-display)' }}>Documents Required</h3>
            <p className="text-amber-800 text-sm mt-0.5 mb-3">
              The following documents are needed to continue processing your claim. Your claim is not rejected — please upload the missing documents.
            </p>
            <div className="space-y-2">
              {missingDocs.map(doc => (
                <div key={doc.type} className="flex items-center justify-between bg-white border border-amber-200 rounded-lg px-3 py-2">
                  <span className="text-sm font-semibold text-amber-800">📋 {doc.type}</span>
                  <DocStatusChip status={doc.status} />
                </div>
              ))}
            </div>
            {claim.decision?.customerMessage && (
              <p className="text-amber-700 text-xs mt-3">{claim.decision.customerMessage}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (claim.status === 'UNDER_HUMAN_REVIEW') {
    return (
      <div className="bg-violet-600 rounded-2xl p-6 text-white">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">🔍</div>
          <div>
            <h3 className="text-lg font-bold mb-0.5" style={{ fontFamily: 'var(--font-display)' }}>Under Human Review</h3>
            <p className="text-white/80 text-sm mt-1 leading-relaxed">
              Your claim has been referred to a certified AXA assessor for review. This happens when the claim requires human judgment — for example, when the claim amount exceeds the auto-approval cap.
            </p>
            <p className="text-white/60 text-xs mt-3">You will be notified when a decision is made.</p>
          </div>
        </div>
      </div>
    );
  }

  if (claim.status === 'PROCESSING') {
    return (
      <div className="border border-blue-200 bg-blue-50 rounded-2xl p-5">
        <div className="flex items-center gap-4">
          <Spinner size="lg" />
          <div>
            <h3 className="font-semibold text-blue-900" style={{ fontFamily: 'var(--font-display)' }}>Processing</h3>
            <p className="text-blue-700 text-sm mt-0.5">Your claim is being reviewed. This usually takes a few minutes.</p>
          </div>
        </div>
      </div>
    );
  }

  if (claim.status === 'BELOW_DEDUCTIBLE') {
    return (
      <div className="border-2 border-gray-300 bg-gray-50 rounded-2xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-gray-200 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">⬇</div>
          <div>
            <h3 className="text-base font-bold text-gray-800 mb-0.5" style={{ fontFamily: 'var(--font-display)' }}>
              Below Deductible
            </h3>
            <p className="text-gray-600 text-sm mt-1 leading-relaxed">
              Your claim is covered, but the claimed amount is at or below your policy deductible. No payment is made for claims at or below the deductible (Clause 0.4). Your policy remains in force.
            </p>
            {claim.decision?.customerMessage && (
              <p className="text-gray-600 text-sm mt-3 leading-relaxed italic">{claim.decision.customerMessage}</p>
            )}
            {claim.decision?.handbookClause && (
              <p className="text-gray-400 text-xs mt-3">Reference: {claim.decision.handbookClause}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}

function DecisionCard({ claim }: { claim: Claim }) {
  if (!claim.decision) return null;

  return (
    <Card className="p-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Decision Details</p>
      {claim.decision.outcome && <DataRow label="Final system decision" value={claim.decision.outcome.replaceAll('_', ' ')} />}
      {claim.decision.reason && <p className="text-sm text-gray-600 mt-3">{claim.decision.reason}</p>}
      {!!claim.decision.decisionTrace?.length && <div className="mt-4 border-t pt-3"><p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Decision trace</p>{claim.decision.decisionTrace.map((item, index) => <div key={`${item.rule}-${index}`} className="text-sm mt-2"><span className={item.result === 'passed' ? 'text-green-700' : item.result === 'failed' ? 'text-red-700' : 'text-gray-500'}>{item.result === 'passed' ? '✓' : item.result === 'failed' ? '×' : '–'} {item.rule.replaceAll('_', ' ')}</span><p className="text-gray-600 ml-4">{item.details}</p></div>)}</div>}
      {claim.status === 'APPROVED' && (
        <div className="space-y-2">
          <DataRow label="Claimed" value={<Amount value={claim.claimedAmount} size="sm" />} />
          {claim.decision.deductible != null && (
            <DataRow label="Deductible" value={`− EGP ${claim.decision.deductible.toLocaleString()}`} />
          )}
          {claim.decision.approvedAmount != null && (
            <DataRow label="Approved amount" value={<Amount value={claim.decision.approvedAmount} />} />
          )}
        </div>
      )}
      {claim.decision.outcome && (
        <p className="text-xs font-mono text-gray-500 mt-2">{claim.decision.outcome}</p>
      )}
    </Card>
  );
}
