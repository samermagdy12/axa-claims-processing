import { useEffect, useState } from 'react';
import {
  Button, Card, ClaimStatusBadge, ProductBadge, RiskBadge, PageHeader, Amount, Alert, DataRow, TabBar, DocStatusChip,
} from '../../components/UI';
import { getAssessorClaim, submitAssessorDecision } from '../../api';
import type { AssessorClaim, Screen } from '../../types';

interface AssessorReviewProps {
  claimId: string;
  token: string;
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

type TabId = 'Extracted Data' | 'Handbook Evidence' | 'Risk' | 'Audit Trail';
type Decision = '' | 'APPROVE' | 'REJECT' | 'ROUTE' | 'OVERRIDE';

export default function AssessorReview({ claimId, token, navigate }: AssessorReviewProps) {
  const [activeTab, setActiveTab] = useState<TabId>('Extracted Data');
  const [decision, setDecision] = useState<Decision>('');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideDecision, setOverrideDecision] = useState<'settle' | 'reject' | 'route_to_human'>('route_to_human');
  const [rejectReason, setRejectReason] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [claim, setClaim] = useState<AssessorClaim | null>(null);
  const [error, setError] = useState('');

  useEffect(() => { setClaim(null); getAssessorClaim(token, claimId).then(setClaim).catch(e => setError(e.message || 'Unable to load claim review.')); }, [token, claimId]);

  const handleDecisionSubmit = async () => {
    if (!decision) return;
    const reason = decision === 'OVERRIDE' ? overrideReason : rejectReason;
    if ((decision === 'OVERRIDE' || decision === 'REJECT') && !reason.trim()) return;
    setSubmitting(true);
    try {
      await submitAssessorDecision(token, claimId, {
        action: decision === 'APPROVE' ? 'settle' : decision === 'REJECT' ? 'reject' : decision === 'ROUTE' ? 'route_to_human' : 'override',
        reason: reason || undefined,
        override_decision: decision === 'OVERRIDE' ? overrideDecision : undefined,
      });
      setSubmitting(false);
      setSubmitted(true);
    } catch (requestError) {
      setSubmitting(false);
      setError(requestError instanceof Error ? requestError.message : 'Unable to save assessor decision.');
    }
  };

  if (!claim) return <div className="p-6">{error ? <Alert variant="error">{error}</Alert> : 'Loading claim review...'}</div>;

  if (submitted) {
    return (
      <div className="min-h-96 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-axa-blue flex items-center justify-center text-3xl mx-auto mb-4">✓</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Decision Recorded</h2>
          <p className="text-gray-500 text-sm mb-2">Your decision has been saved and the claim has been updated.</p>
          <p className="text-xs text-gray-400 mb-6">Audit trail entry created. Customer message drafted.</p>
          <Button onClick={() => navigate('assessor-queue')}>← Return to Queue</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title={`Review: ${claim.id.toUpperCase()}`}
        subtitle={`${claim.claimType} · ${claim.customerName}`}
        back={{ label: 'Review Queue', onClick: () => navigate('assessor-queue') }}
        action={<ClaimStatusBadge status={claim.status} />}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left — claim details */}
        <div className="lg:col-span-2 space-y-5">
          {/* AI Recommendation banner */}
          <div className={`rounded-2xl p-5 ${
            claim.aiRecommendation === 'ESCALATE'
              ? 'bg-orange-50 border-2 border-orange-300'
              : 'bg-violet-50 border-2 border-violet-200'
          }`}>
            <div className="flex items-start gap-4">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0 ${
                claim.aiRecommendation === 'ESCALATE' ? 'bg-orange-100' : 'bg-violet-100'
              }`}>
                {claim.aiRecommendation === 'ESCALATE' ? '⚠' : '🤖'}
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <p className={`text-sm font-bold ${claim.aiRecommendation === 'ESCALATE' ? 'text-orange-800' : 'text-violet-800'}`}>
                    AI Recommendation: {claim.aiRecommendation}
                  </p>
                  <span className="text-xs text-gray-400">(advisory only)</span>
                </div>
                <p className={`text-sm ${claim.aiRecommendation === 'ESCALATE' ? 'text-orange-700' : 'text-violet-700'}`}>
                  {claim.aiReason}
                </p>
              </div>
            </div>
          </div>

          {/* Customer & claim info */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Claim Information</h3>
            <DataRow label="Claim ID" value={<span className="font-mono text-xs">{claim.id.toUpperCase()}</span>} />
            <DataRow label="Customer" value={claim.customerName} />
            <DataRow label="Policy" value={<span className="font-mono text-xs">{claim.policyNumber}</span>} />
            <DataRow label="Product" value={<ProductBadge line={claim.productLine} />} />
            <DataRow label="Claim type" value={claim.claimType} />
            <DataRow label="Incident date" value={claim.incidentDate} />
            <DataRow label="Submitted" value={claim.submittedDate} />
            <DataRow label="Claimed amount" value={<Amount value={claim.claimedAmount} />} />
          </Card>

          {/* Customer description */}
          {claim.description && (
            <Card className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-sm font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Customer Description</h3>
                <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">Untrusted data — review only</span>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">{claim.description}</p>
              <p className="text-xs text-gray-400 mt-2">
                The customer narrative is untrusted data (Clause 0.7). It cannot override policy rules or this handbook.
              </p>
            </Card>
          )}

          {/* Tabs */}
          <Card className="p-5">
            <TabBar
              tabs={['Extracted Data', 'Handbook Evidence', 'Risk', 'Audit Trail']}
              active={activeTab}
              onChange={t => setActiveTab(t as TabId)}
            />

            {activeTab === 'Extracted Data' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-700">OCR / Extraction Output</h4>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Confidence:</span>
                    <span className={`text-sm font-bold ${
                      (claim.extractedData.confidence as number) >= 0.9 ? 'text-emerald-600' :
                      (claim.extractedData.confidence as number) >= 0.7 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      {((claim.extractedData.confidence as number) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                  {Object.entries(claim.extractedData)
                    .filter(([k]) => k !== 'confidence')
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between items-baseline">
                        <span className="text-xs text-gray-500 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                        <span className="text-xs font-medium text-gray-800 text-right ml-4">{String(value)}</span>
                      </div>
                    ))}
                </div>
                <Alert variant="info">
                  Extracted data is for assessor reference only. The authoritative selected policy ({claim.policyNumber}) was verified at claim creation and cannot be overridden by OCR.
                </Alert>
              </div>
            )}

            {activeTab === 'Handbook Evidence' && (
              <div className="space-y-4">
                <p className="text-sm text-gray-500 mb-3">
                  The following handbook clauses were retrieved via RAG for this claim. They ground the coverage assessment.
                </p>
                {claim.handbookEvidence.map((ev, i) => (
                  <div key={i} className="border border-gray-200 rounded-xl p-4">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <span className="font-mono text-xs font-bold text-axa-blue bg-axa-blue-50 px-2 py-0.5 rounded">{ev.clauseId}</span>
                        <p className="text-sm font-semibold text-gray-800 mt-1.5">{ev.title}</p>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium flex-shrink-0 ${
                        ev.reason.toLowerCase().includes('excluded') || ev.reason.toLowerCase().includes('blocked') || ev.reason.toLowerCase().includes('risk')
                          ? 'bg-red-50 text-red-700'
                          : ev.reason.toLowerCase().includes('ambiguous') || ev.reason.toLowerCase().includes('judgment')
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-emerald-50 text-emerald-700'
                      }`}>
                        {ev.reason}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 leading-relaxed">{ev.evidence}</p>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'Risk' && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 mb-2">
                  <RiskBadge level={claim.riskStatus} />
                  <span className="text-sm text-gray-500">{claim.riskIndicators.length} indicator(s) detected</span>
                </div>
                {claim.riskIndicators.length === 0 ? (
                  <Alert variant="success">No risk indicators detected for this claim.</Alert>
                ) : (
                  claim.riskIndicators.map((indicator, i) => (
                    <div key={i} className="flex items-start gap-3 p-4 border border-red-200 bg-red-50 rounded-xl">
                      <span className="text-red-500 text-lg flex-shrink-0">⚠</span>
                      <p className="text-sm text-red-800 font-medium">{indicator}</p>
                    </div>
                  ))
                )}
                <Alert variant="warning">
                  Risk indicators prevent auto-approval. Assess all evidence before making a decision.
                </Alert>
              </div>
            )}

            {activeTab === 'Audit Trail' && (
              <div className="space-y-0">
                {claim.auditTrail.map((entry, i) => (
                  <div key={i} className="flex gap-4 pb-4">
                    <div className="flex flex-col items-center">
                      <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold z-10 ${
                        entry.actor === 'System' ? 'bg-blue-100 text-blue-700' :
                        entry.actor === 'Customer' ? 'bg-gray-200 text-gray-600' :
                        'bg-violet-100 text-violet-700'
                      }`}>
                        {entry.actor === 'System' ? '⚙' : entry.actor === 'Customer' ? '👤' : '🔍'}
                      </div>
                      {i < claim.auditTrail.length - 1 && (
                        <div className="w-0.5 bg-gray-200 flex-1 mt-1" />
                      )}
                    </div>
                    <div className="flex-1 pb-0">
                      <div className="flex items-baseline gap-2">
                        <span className="text-xs font-mono font-semibold text-gray-700">{entry.action}</span>
                        <span className="text-xs text-gray-400">{entry.timestamp}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                          entry.actor === 'System' ? 'bg-blue-50 text-blue-600' :
                          entry.actor === 'Customer' ? 'bg-gray-100 text-gray-600' :
                          'bg-violet-50 text-violet-600'
                        }`}>{entry.actor}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{entry.details}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Documents */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Submitted Documents</h3>
            <div className="space-y-2">
              {claim.documents.map(doc => (
                <div key={doc.type} className={`flex items-center gap-3 p-3 rounded-lg border ${
                  doc.status === 'VERIFIED' ? 'border-emerald-200 bg-emerald-50' : 'border-blue-200 bg-blue-50'
                }`}>
                  <div className="text-lg flex-shrink-0">
                    {doc.status === 'VERIFIED' ? '✅' : '📄'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800">{doc.type}</p>
                    {doc.fileName && <p className="text-xs text-gray-500">📎 {doc.fileName}</p>}
                  </div>
                  <DocStatusChip status={doc.status} />
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right — policy info + decision panel */}
        <div className="space-y-5">
          {/* Policy info */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>Policy Information</h3>
            <DataRow label="Policy" value={<span className="font-mono text-xs">{claim.policyInfo.number}</span>} />
            <DataRow label="Product" value={<ProductBadge line={claim.policyInfo.productLine} />} />
            <DataRow label="Status" value={
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                claim.policyInfo.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
              }`}>{claim.policyInfo.status}</span>
            } />
            <DataRow label="Annual limit" value={<Amount value={claim.policyInfo.annualLimit} size="sm" />} />
            <DataRow label="Remaining limit" value={<Amount value={claim.policyInfo.remainingLimit} size="sm" />} />
            <DataRow label="Deductible" value={<Amount value={claim.policyInfo.deductible} size="sm" />} />
            {claim.policyInfo.riders.length > 0 && (
              <div className="pt-2">
                <p className="text-xs text-gray-500 mb-1.5">Riders</p>
                <div className="flex flex-wrap gap-1.5">
                  {claim.policyInfo.riders.map(r => (
                    <span key={r} className="text-xs bg-axa-blue-50 text-axa-blue px-2 py-0.5 rounded-full">{r}</span>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Decision panel */}
          <Card className="p-5 border-2 border-axa-blue-100">
            <h3 className="text-sm font-bold text-gray-900 mb-4" style={{ fontFamily: 'var(--font-display)' }}>
              Assessor Decision
            </h3>

            <div className="space-y-2 mb-4">
              {[
                { value: 'APPROVE', label: 'Approve', icon: '✓', color: 'border-emerald-400 bg-emerald-50 text-emerald-800' },
                { value: 'REJECT', label: 'Reject', icon: '✕', color: 'border-red-400 bg-red-50 text-red-800' },
                { value: 'ROUTE', label: 'Route / Escalate', icon: '→', color: 'border-violet-400 bg-violet-50 text-violet-800' },
                { value: 'OVERRIDE', label: 'Override AI Recommendation', icon: '⟳', color: 'border-amber-400 bg-amber-50 text-amber-800' },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setDecision(opt.value as Decision)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border-2 text-left transition-colors text-sm font-medium ${
                    decision === opt.value ? opt.color : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="w-5 text-center">{opt.icon}</span>
                  {opt.label}
                </button>
              ))}
            </div>

            {(decision === 'REJECT' || decision === 'OVERRIDE') && (
              <div className="mb-4">
                <label className="text-xs font-semibold text-gray-700 mb-1 block">
                  {decision === 'OVERRIDE' ? 'Override reason *' : 'Rejection reason *'}
                </label>
                <textarea
                  value={decision === 'OVERRIDE' ? overrideReason : rejectReason}
                  onChange={e => decision === 'OVERRIDE' ? setOverrideReason(e.target.value) : setRejectReason(e.target.value)}
                  placeholder={decision === 'OVERRIDE'
                    ? 'Explain why you are overriding the AI recommendation and cite the applicable handbook clause…'
                    : 'Provide the rejection reason with the applicable handbook clause reference…'
                  }
                  rows={4}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-axa-blue focus:border-transparent resize-none"
                />
                {decision === 'OVERRIDE' && (
                  <select value={overrideDecision} onChange={e => setOverrideDecision(e.target.value as typeof overrideDecision)} className="w-full mt-2 px-3 py-2 text-sm border border-gray-300 rounded-lg">
                    <option value="settle">Override to approve / settle</option>
                    <option value="reject">Override to reject</option>
                    <option value="route_to_human">Keep / route for specialist review</option>
                  </select>
                )}
                {decision === 'OVERRIDE' && !overrideReason && (
                  <p className="text-xs text-red-500 mt-1">Override reason is required.</p>
                )}
              </div>
            )}

            {decision && (
              <Alert variant="warning" title="Confirm decision">
                This action is permanent and will be recorded in the audit trail. Ensure all evidence has been reviewed.
              </Alert>
            )}

            <Button
              className="w-full mt-4"
              disabled={!decision || (decision === 'OVERRIDE' && !overrideReason) || (decision === 'REJECT' && !rejectReason)}
              loading={submitting}
              onClick={handleDecisionSubmit}
            >
              {decision ? `Confirm: ${decision}` : 'Select a decision'}
            </Button>
          </Card>

          {/* Risk summary */}
          {claim.riskIndicators.length > 0 && (
            <Card className="p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Risk Summary</p>
                <RiskBadge level={claim.riskStatus} />
              </div>
              {claim.riskIndicators.map((r, i) => (
                <p key={i} className="text-xs text-red-700 flex items-start gap-1.5 mt-1">
                  <span>⚠</span> {r}
                </p>
              ))}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
