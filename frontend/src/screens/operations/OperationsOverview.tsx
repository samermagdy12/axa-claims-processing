import { Card, PageHeader, Amount, ProgressBar } from '../../components/UI';
import { OPERATIONS_DATA } from '../../data';

const PRODUCT_STYLES: Record<string, { icon: string; bg: string; text: string; accent: string }> = {
  HEALTH: { icon: '🏥', bg: 'bg-emerald-50', text: 'text-emerald-700', accent: 'bg-emerald-500' },
  MOTOR: { icon: '🚗', bg: 'bg-blue-50', text: 'text-blue-700', accent: 'bg-blue-500' },
  PROPERTY: { icon: '🏠', bg: 'bg-amber-50', text: 'text-amber-700', accent: 'bg-amber-500' },
  TRAVEL: { icon: '✈️', bg: 'bg-violet-50', text: 'text-violet-700', accent: 'bg-violet-500' },
};

const LABELS: Record<string, string> = {
  HEALTH: 'Health',
  MOTOR: 'Motor',
  PROPERTY: 'Property',
  TRAVEL: 'Travel',
};

export default function OperationsOverview() {
  const lines = Object.keys(OPERATIONS_DATA) as (keyof typeof OPERATIONS_DATA)[];
  const totals = lines.reduce(
    (acc, line) => {
      const d = OPERATIONS_DATA[line];
      acc.processed += d.processed;
      acc.approved += d.approved;
      acc.routed += d.routed;
      acc.rejected += d.rejected;
      acc.riskFlagged += d.riskFlagged;
      return acc;
    },
    { processed: 0, approved: 0, routed: 0, rejected: 0, riskFlagged: 0 }
  );

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Operations Overview"
        subtitle="Read-only processing summary by product line"
      />

      <div className="mb-4 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        <span className="text-xs text-gray-500">Live data · Read-only view · Operations cannot make claim decisions</span>
      </div>

      {/* Summary totals */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-8">
        {[
          { label: 'Total Processed', value: totals.processed, color: 'text-gray-900' },
          { label: 'Approved', value: totals.approved, color: 'text-emerald-600' },
          { label: 'Routed to Human', value: totals.routed, color: 'text-violet-600' },
          { label: 'Rejected', value: totals.rejected, color: 'text-red-600' },
          { label: 'Risk Flagged', value: totals.riskFlagged, color: 'text-amber-600' },
        ].map(({ label, value, color }) => (
          <Card key={label} className="p-4 text-center">
            <p className={`text-2xl font-bold ${color}`} style={{ fontFamily: 'var(--font-display)' }}>{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </Card>
        ))}
      </div>

      {/* Product line breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-8">
        {lines.map(line => {
          const d = OPERATIONS_DATA[line];
          const style = PRODUCT_STYLES[line];
          const approvalRate = d.processed > 0 ? ((d.approved / d.processed) * 100).toFixed(0) : '0';

          return (
            <Card key={line} className="p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${style.bg}`}>
                    {style.icon}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{LABELS[line]}</p>
                    <p className="text-xs text-gray-400">{d.processed} claims processed</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${style.text}`} style={{ fontFamily: 'var(--font-display)' }}>
                    {approvalRate}%
                  </p>
                  <p className="text-xs text-gray-400">approval rate</p>
                </div>
              </div>

              {/* Outcome bars */}
              <div className="space-y-3">
                {[
                  { label: 'Approved', value: d.approved, max: d.processed, barColor: 'bg-emerald-500', textColor: 'text-emerald-600' },
                  { label: 'Routed to Human', value: d.routed, max: d.processed, barColor: 'bg-violet-500', textColor: 'text-violet-600' },
                  { label: 'Rejected', value: d.rejected, max: d.processed, barColor: 'bg-red-400', textColor: 'text-red-600' },
                  { label: 'Risk Flagged', value: d.riskFlagged, max: d.processed, barColor: 'bg-amber-400', textColor: 'text-amber-600' },
                ].map(({ label, value, max, barColor, textColor }) => (
                  <div key={label}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-gray-500">{label}</span>
                      <span className={`text-xs font-bold ${textColor}`}>{value}</span>
                    </div>
                    <ProgressBar value={value} max={max} colorClass={barColor} />
                  </div>
                ))}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Full table */}
      <Card>
        <div className="p-5 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Detailed Counts</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {['Product Line', 'Processed', 'Approved', 'Routed to Human', 'Rejected', 'Risk Flagged', 'Approval Rate'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lines.map(line => {
                const d = OPERATIONS_DATA[line];
                const style = PRODUCT_STYLES[line];
                const rate = d.processed > 0 ? ((d.approved / d.processed) * 100).toFixed(1) : '—';
                return (
                  <tr key={line} className="hover:bg-gray-50">
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <span>{style.icon}</span>
                        <span className={`font-semibold ${style.text}`}>{LABELS[line]}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 font-bold text-gray-900">{d.processed}</td>
                    <td className="px-4 py-4 text-emerald-600 font-semibold">{d.approved}</td>
                    <td className="px-4 py-4 text-violet-600 font-semibold">{d.routed}</td>
                    <td className="px-4 py-4 text-red-600 font-semibold">{d.rejected}</td>
                    <td className="px-4 py-4 text-amber-600 font-semibold">{d.riskFlagged}</td>
                    <td className="px-4 py-4">
                      <span className={`text-sm font-bold ${style.text}`}>{rate}%</span>
                    </td>
                  </tr>
                );
              })}
              {/* Totals row */}
              <tr className="bg-gray-50 border-t-2 border-gray-200 font-bold">
                <td className="px-4 py-4 text-gray-900 text-sm">Total</td>
                <td className="px-4 py-4 text-gray-900">{totals.processed}</td>
                <td className="px-4 py-4 text-emerald-700">{totals.approved}</td>
                <td className="px-4 py-4 text-violet-700">{totals.routed}</td>
                <td className="px-4 py-4 text-red-700">{totals.rejected}</td>
                <td className="px-4 py-4 text-amber-700">{totals.riskFlagged}</td>
                <td className="px-4 py-4 text-gray-700">
                  {totals.processed > 0 ? ((totals.approved / totals.processed) * 100).toFixed(1) : '—'}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      <p className="text-xs text-gray-400 mt-4 text-center">
        Operations view is read-only. Claim decisions are made by the processing system and certified assessors only.
      </p>
    </div>
  );
}
