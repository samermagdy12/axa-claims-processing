import { useEffect, useState } from 'react';
import { Alert, Button } from '../../components/UI';
import { getProcessingSummary } from '../../api';
import type { DocumentValidation, ProcessingSummary } from '../../api';
import type { Screen } from '../../types';

interface ClaimProcessingProps {
  claimId: string;
  documentsProcessed: number;
  extractionsCompleted: number;
  processingFailures: number;
  validationResults: string;
  token: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function ClaimProcessing({ claimId, documentsProcessed, extractionsCompleted, processingFailures, validationResults, token, navigate }: ClaimProcessingProps) {
  const results = parseValidationResults(validationResults);
  const [summary, setSummary] = useState<ProcessingSummary | null>(null);
  useEffect(() => { getProcessingSummary(token, claimId).then(setSummary).catch(() => setSummary(null)); }, [token, claimId]);
  const documentsChecked = processingFailures === 0;
  const blocked = Boolean(summary?.missing_documents.length || summary?.invalid_documents.length || summary?.manual_review_required);
  const pipeline = summary?.pipeline || {};
  const stages = [
    { label: 'Claim Received', detail: 'Your claim was submitted successfully.', complete: true },
    { label: 'Document Processing', detail: `${documentsProcessed} uploaded document${documentsProcessed === 1 ? '' : 's'} processed.`, complete: documentsProcessed > 0 },
    { label: 'Information Extracted', detail: `${extractionsCompleted} real extraction record${extractionsCompleted === 1 ? '' : 's'} saved.`, complete: extractionsCompleted > 0 },
    { label: 'Required Documents Checked', detail: blocked ? `Processing is waiting for: ${[...(summary?.missing_documents || []), ...(summary?.invalid_documents || []).map(() => 'a corrected document')].join(', ')}.` : documentsChecked ? 'All required documents are present and valid.' : 'Some selected documents could not be processed; review the claim checklist.', complete: documentsChecked && !blocked },
    { label: 'Policy Validated', detail: blocked ? 'Waiting for required documents.' : pipeline.policy_validation === 'completed' ? 'Policy eligibility was validated.' : 'Processing policy eligibility.', complete: pipeline.policy_validation === 'completed' },
    { label: 'Coverage Checked', detail: blocked ? 'Waiting for required documents.' : pipeline.coverage_check === 'completed' ? 'Coverage was checked against applicable handbook evidence.' : 'Checking coverage.', complete: pipeline.coverage_check === 'completed' },
    { label: 'Risk Checks Complete', detail: blocked ? 'Waiting for required documents.' : pipeline.risk_check === 'completed' ? 'Risk and consistency signals were evaluated.' : 'Checking risk signals.', complete: pipeline.risk_check === 'completed' },
    { label: 'Decision Made', detail: blocked ? 'A final decision will be made after document requirements are met.' : summary?.final_decision ? `Final system decision: ${summary.final_decision.outcome.replaceAll('_', ' ')}.` : 'Completing automatic decision.', complete: pipeline.decision === 'completed' },
  ];

  return <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4"><div className="w-full max-w-lg">
    <div className="text-center mb-8"><div className="w-16 h-16 rounded-2xl bg-axa-blue flex items-center justify-center text-3xl mx-auto mb-4">✓</div><h1 className="text-xl font-bold text-gray-900">Claim Submitted</h1><p className="text-sm text-gray-500 mt-1">Reference: <span className="font-mono font-semibold text-gray-700">{claimId}</span></p></div>
    {processingFailures > 0 && <Alert variant="warning" title="Some document processing needs attention" className="mb-5">{processingFailures} selected document{processingFailures === 1 ? '' : 's'} could not be uploaded or extracted. Your claim was saved; open it to review the required-document checklist.</Alert>}
    {results.length > 0 && <div className="bg-white border border-gray-200 rounded-2xl p-5 mb-5 space-y-3"><h2 className="text-sm font-semibold text-gray-900">Document validation</h2>{results.map(({ documentType, validation }) => <ValidationResult key={documentType} documentType={documentType} validation={validation} onReplace={() => navigate('claim-details', { selectedClaimId: claimId, processingValidationResults: validationResults })} />)}</div>}
    <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-5 space-y-5">{stages.map((stage, index) => <div key={stage.label} className="flex gap-4"><div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${stage.complete ? 'bg-emerald-500 text-white' : 'bg-gray-200 text-gray-500'}`}>{stage.complete ? '✓' : index + 1}</div><div><p className={`text-sm font-semibold ${stage.complete ? 'text-emerald-700' : 'text-gray-500'}`}>{stage.label}</p><p className="text-xs text-gray-500 mt-0.5">{stage.detail}</p></div></div>)}</div>
    <div className="bg-axa-blue rounded-2xl p-6 text-center"><p className="text-white font-semibold text-lg mb-1">{blocked ? 'Action required to continue processing' : 'Your claim is being processed automatically'}</p><p className="text-white/70 text-sm mb-5">{blocked ? 'Upload or replace the indicated documents. Processing resumes automatically after validation.' : 'Policy, coverage, risk, and final decision checks run automatically after document validation.'}</p><div className="flex gap-3 justify-center"><Button variant="outline" className="bg-white/10 border-white/30 text-white hover:bg-white/20" onClick={() => navigate('my-claims')}>View All Claims</Button><Button className="bg-white text-axa-blue hover:bg-axa-blue-100" onClick={() => navigate('claim-details', { selectedClaimId: claimId })}>View Claim</Button></div></div>
  </div></div>;
}

function parseValidationResults(value: string): { documentType: string; validation: DocumentValidation }[] {
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter(item => item && typeof item.documentType === 'string' && item.validation) : [];
  } catch {
    return [];
  }
}

function ValidationResult({ documentType, validation, onReplace }: { documentType: string; validation: DocumentValidation; onReplace: () => void }) {
  const invalid = validation.status === 'invalid' || validation.status === 'failed';
  const color = validation.status === 'valid' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : invalid ? 'border-red-200 bg-red-50 text-red-900' : 'border-amber-200 bg-amber-50 text-amber-900';
  return <div className={`border rounded-xl p-3 text-sm ${color}`}><p className="font-semibold">{validation.status === 'valid' ? '✓ Valid document' : invalid ? '✕ Wrong document uploaded' : '⚠ Document needs attention'}: {documentType}</p><p className="text-xs mt-1">{validation.message}</p>{validation.status === 'invalid' && <div className="text-xs mt-2 space-y-0.5">{validation.errors.map(error => <p key={error}>{error}</p>)}<Button size="sm" variant="outline" className="mt-2" onClick={onReplace}>Replace document</Button></div>}{validation.status === 'warning' && validation.warnings.map(warning => <p className="text-xs mt-2" key={warning}>{warning}</p>)}</div>;
}
