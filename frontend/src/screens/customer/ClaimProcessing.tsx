import { Alert, Button } from '../../components/UI';
import type { Screen } from '../../types';

interface ClaimProcessingProps {
  claimId: string;
  documentsProcessed: number;
  extractionsCompleted: number;
  processingFailures: number;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function ClaimProcessing({ claimId, documentsProcessed, extractionsCompleted, processingFailures, navigate }: ClaimProcessingProps) {
  const documentsChecked = processingFailures === 0;
  const stages = [
    { label: 'Claim Received', detail: 'Your claim was submitted successfully.', complete: true },
    { label: 'Document Processing', detail: `${documentsProcessed} uploaded document${documentsProcessed === 1 ? '' : 's'} processed.`, complete: documentsProcessed > 0 },
    { label: 'Information Extracted', detail: `${extractionsCompleted} real extraction record${extractionsCompleted === 1 ? '' : 's'} saved.`, complete: extractionsCompleted > 0 },
    { label: 'Required Documents Checked', detail: documentsChecked ? 'The uploaded-document checklist was updated.' : 'Some selected documents could not be processed; review the claim checklist.', complete: documentsChecked },
    { label: 'Policy Validated', detail: 'Not implemented in this phase.', complete: false },
    { label: 'Coverage Checked', detail: 'Not implemented in this phase.', complete: false },
    { label: 'Risk Checks Complete', detail: 'Not implemented in this phase.', complete: false },
    { label: 'Decision Made', detail: 'Not implemented in this phase.', complete: false },
  ];

  return <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4"><div className="w-full max-w-lg">
    <div className="text-center mb-8"><div className="w-16 h-16 rounded-2xl bg-axa-blue flex items-center justify-center text-3xl mx-auto mb-4">✓</div><h1 className="text-xl font-bold text-gray-900">Claim Submitted</h1><p className="text-sm text-gray-500 mt-1">Reference: <span className="font-mono font-semibold text-gray-700">{claimId}</span></p></div>
    {processingFailures > 0 && <Alert variant="warning" title="Some document processing needs attention" className="mb-5">{processingFailures} selected document{processingFailures === 1 ? '' : 's'} could not be uploaded or extracted. Your claim was saved; open it to review the required-document checklist.</Alert>}
    <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-5 space-y-5">{stages.map((stage, index) => <div key={stage.label} className="flex gap-4"><div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-bold ${stage.complete ? 'bg-emerald-500 text-white' : 'bg-gray-200 text-gray-500'}`}>{stage.complete ? '✓' : index + 1}</div><div><p className={`text-sm font-semibold ${stage.complete ? 'text-emerald-700' : 'text-gray-500'}`}>{stage.label}</p><p className="text-xs text-gray-500 mt-0.5">{stage.detail}</p></div></div>)}</div>
    <div className="bg-axa-blue rounded-2xl p-6 text-center"><p className="text-white font-semibold text-lg mb-1">Your claim is ready for the next available step</p><p className="text-white/70 text-sm mb-5">Only claim submission, document processing, extraction, and checklist updates are completed here.</p><div className="flex gap-3 justify-center"><Button variant="outline" className="bg-white/10 border-white/30 text-white hover:bg-white/20" onClick={() => navigate('my-claims')}>View All Claims</Button><Button className="bg-white text-axa-blue hover:bg-axa-blue-100" onClick={() => navigate('claim-details', { selectedClaimId: claimId })}>View Claim</Button></div></div>
  </div></div>;
}
