import { Card, Button, ClaimStatusBadge, ProductBadge, RiskBadge, PageHeader, Amount, Alert } from '../../components/UI';
import { ASSESSOR_CLAIMS } from '../../data';
import type { Screen } from '../../types';

interface AssessorQueueProps {
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function AssessorQueue({ navigate }: AssessorQueueProps) {
  const queue = ASSESSOR_CLAIMS;
  const highRisk = queue.filter(c => c.riskStatus === 'HIGH').length;
  const escalated = queue.filter(c => c.aiRecommendation === 'ESCALATE').length;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Human Review Queue"
        subtitle={`${queue.length} claims awaiting assessor review`}
      />

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Total in queue', value: queue.length, color: 'text-axa-blue' },
          { label: 'High risk', value: highRisk, color: 'text-red-600' },
          { label: 'Escalated', value: escalated, color: 'text-orange-600' },
        ].map(({ label, value, color }) => (
          <Card key={label} className="p-4 text-center">
            <p className={`text-2xl font-bold ${color}`} style={{ fontFamily: 'var(--font-display)' }}>{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </Card>
        ))}
      </div>

      {/* Queue table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {['Claim ID', 'Customer', 'Policy', 'Product', 'Claim Type', 'Amount', 'Date', 'Status', 'Risk', 'AI Rec.', 'Action'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {queue.map(claim => (
                <tr key={claim.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-4">
                    <span className="font-mono text-xs font-semibold text-gray-700">{claim.id.toUpperCase()}</span>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-sm font-medium text-gray-800">{claim.customerName}</span>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-mono text-gray-500">{claim.policyNumber}</span>
                  </td>
                  <td className="px-4 py-4">
                    <ProductBadge line={claim.productLine} />
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-sm text-gray-700">{claim.claimType}</span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <Amount value={claim.claimedAmount} size="sm" />
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className="text-xs text-gray-500">{claim.submittedDate}</span>
                  </td>
                  <td className="px-4 py-4">
                    <ClaimStatusBadge status={claim.status} />
                  </td>
                  <td className="px-4 py-4">
                    <RiskBadge level={claim.riskStatus} />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-col gap-0.5">
                      <span className={`text-xs font-semibold ${
                        claim.aiRecommendation === 'ESCALATE' ? 'text-orange-600' : 'text-violet-600'
                      }`}>
                        {claim.aiRecommendation === 'ESCALATE' ? '⚠ ESCALATE' : '→ ROUTE'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <Button
                      size="sm"
                      onClick={() => navigate('assessor-review', { selectedAssessorClaimId: claim.id })}
                    >
                      Review →
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-500">
        <span>AI recommendations are advisory only.</span>
        <span>Assessors review all evidence before making a decision.</span>
        <span>Override requires a written reason.</span>
      </div>
    </div>
  );
}
