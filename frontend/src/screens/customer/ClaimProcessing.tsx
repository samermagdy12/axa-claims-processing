import { useEffect, useState } from 'react';
import { Button } from '../../components/UI';
import type { Screen } from '../../types';

interface ClaimProcessingProps {
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

const STAGES = [
  { id: 'received', label: 'Claim Received', detail: 'Your claim has been securely submitted and assigned a reference ID.', duration: 600 },
  { id: 'documents', label: 'Document Processing', detail: 'Uploaded files are stored securely and sent for OCR extraction.', duration: 900 },
  { id: 'extraction', label: 'Information Extracted', detail: 'Structured data extracted from your documents with confidence scoring.', duration: 800 },
  { id: 'docs_check', label: 'Required Documents Checked', detail: 'Verifying all required documents are present for your claim type.', duration: 700 },
  { id: 'policy', label: 'Policy Validated', detail: 'Policy status, dates, and applicable waiting periods verified.', duration: 800 },
  { id: 'coverage', label: 'Coverage Checked', detail: 'Handbook clauses retrieved and coverage validated against your policy.', duration: 1000 },
  { id: 'risk', label: 'Risk Checks Complete', detail: 'Duplicate detection and fraud-risk indicators assessed.', duration: 800 },
  { id: 'decision', label: 'Decision Made', detail: 'All checks complete. Your claim result is ready.', duration: 600 },
];

export default function ClaimProcessing({ navigate }: ClaimProcessingProps) {
  const [completedStages, setCompletedStages] = useState<string[]>([]);
  const [currentStage, setCurrentStage] = useState(0);
  const [done, setDone] = useState(false);
  const claimRef = `CLM-${Math.floor(Math.random() * 900000 + 100000)}`;

  useEffect(() => {
    let totalDelay = 0;
    STAGES.forEach((stage, i) => {
      const timeout = setTimeout(() => {
        setCurrentStage(i);
        if (i > 0) {
          setCompletedStages(prev => [...prev, STAGES[i - 1].id]);
        }
        if (i === STAGES.length - 1) {
          setTimeout(() => {
            setCompletedStages(STAGES.map(s => s.id));
            setDone(true);
          }, stage.duration);
        }
      }, totalDelay);
      totalDelay += stage.duration;
      return () => clearTimeout(timeout);
    });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-axa-blue flex items-center justify-center text-3xl mx-auto mb-4">
            {done ? '✓' : '⚙'}
          </div>
          <h1 className="text-xl font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>
            {done ? 'Processing Complete' : 'Processing Your Claim'}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Reference:{' '}
            <span className="font-mono font-semibold text-gray-700">{claimRef}</span>
          </p>
        </div>

        {/* Stage timeline */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-5">
          <div className="space-y-0">
            {STAGES.map((stage, i) => {
              const isCompleted = completedStages.includes(stage.id);
              const isCurrent = currentStage === i && !isCompleted;
              const isPending = !isCompleted && !isCurrent;

              return (
                <div key={stage.id} className="flex gap-4">
                  {/* Connector */}
                  <div className="flex flex-col items-center">
                    <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold transition-all z-10 ${
                      isCompleted ? 'bg-emerald-500 text-white' :
                      isCurrent ? 'bg-axa-blue text-white' :
                      'bg-gray-200 text-gray-400'
                    }`}>
                      {isCompleted ? '✓' : isCurrent ? (
                        <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin-slow" />
                      ) : i + 1}
                    </div>
                    {i < STAGES.length - 1 && (
                      <div className={`w-0.5 h-8 mt-1 transition-colors ${isCompleted ? 'bg-emerald-300' : 'bg-gray-200'}`} />
                    )}
                  </div>

                  {/* Content */}
                  <div className="pb-6 last:pb-0 flex-1 min-w-0">
                    <p className={`text-sm font-semibold transition-colors ${
                      isCompleted ? 'text-emerald-700' : isCurrent ? 'text-axa-blue' : 'text-gray-400'
                    }`}>
                      {stage.label}
                    </p>
                    {(isCompleted || isCurrent) && (
                      <p className={`text-xs mt-0.5 ${isCompleted ? 'text-gray-500' : 'text-blue-600'}`}>
                        {stage.detail}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Info note */}
        {!done && (
          <div className="text-center">
            <p className="text-xs text-gray-400">
              Document processing uses OCR extraction to read your files. Coverage decisions are made using the AXA Claims Handbook — not by AI alone.
            </p>
          </div>
        )}

        {/* Done state */}
        {done && (
          <div className="bg-axa-blue rounded-2xl p-6 text-center animate-fade-in">
            <p className="text-white font-semibold text-lg mb-1">Your claim has been processed</p>
            <p className="text-white/70 text-sm mb-5">
              View your claim status and decision below. Additional information may be required.
            </p>
            <div className="flex gap-3 justify-center">
              <Button
                variant="outline"
                className="bg-white/10 border-white/30 text-white hover:bg-white/20"
                onClick={() => navigate('my-claims')}
              >
                View All Claims
              </Button>
              <Button
                className="bg-white text-axa-blue hover:bg-axa-blue-100"
                onClick={() => navigate('claim-details', { selectedClaimId: 'clm-002' })}
              >
                View Claim Result →
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
