import { useState } from 'react';
import { Card, Button, ClaimStatusBadge, ProductBadge, RiskBadge, PageHeader, Amount, TabBar } from '../../components/UI';
import { ASSESSOR_CLAIMS } from '../../data';
import type { Screen } from '../../types';

interface AssessorClaimsProps {
  navigate: (screen: Screen, params?: Record<string, string>) => void;
}

export default function AssessorClaims({ navigate }: AssessorClaimsProps) {
  const [tab, setTab] = useState('All');
  const all = ASSESSOR_CLAIMS;

  const filtered = tab === 'All' ? all :
    tab === 'Escalated' ? all.filter(c => c.aiRecommendation === 'ESCALATE') :
    all.filter(c => c.riskStatus === 'HIGH');

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Claims"
        subtitle="All claims in the human-review workflow"
      />

      <TabBar
        tabs={['All', 'Escalated', 'High Risk']}
        active={tab}
        onChange={setTab}
      />

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {['Claim ID', 'Customer', 'Policy', 'Product', 'Claim Type', 'Amount', 'Date', 'Status', 'Risk', 'AI Rec.', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(claim => (
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
                    <span className={`text-xs font-semibold ${
                      claim.aiRecommendation === 'ESCALATE' ? 'text-orange-600' : 'text-violet-600'
                    }`}>
                      {claim.aiRecommendation}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <Button
                      size="sm"
                      onClick={() => navigate('assessor-review', { selectedAssessorClaimId: claim.id })}
                    >
                      Review
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
