import { useState } from 'react';
import { Card, Button, Input, PageHeader, Alert, DataRow, Amount } from '../../components/UI';
import { useCustomerData } from '../../hooks/useCustomerData';

interface ProfileProps {
  userName: string;
  userEmail: string;
  token: string;
}

export default function Profile({ userName, userEmail, token }: ProfileProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(userName);
  const [saved, setSaved] = useState(false);

  const { policies, claims, loading, error } = useCustomerData(token);
  const activePolicies = policies.filter(p => p.status === 'ACTIVE');
  const approvedClaims = claims.filter(c => c.status === 'APPROVED');
  const totalApproved = approvedClaims.reduce((sum, c) => sum + c.claimedAmount, 0);

  const handleSave = () => {
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="animate-fade-in">
      <PageHeader title="Profile" subtitle="Manage your account and view your policy summary" />

      {saved && <Alert variant="success" className="mb-5">Profile updated successfully.</Alert>}
      {loading && <p className="text-sm text-gray-500 mb-5">Loading your policy and claim summary…</p>}
      {error && <Alert variant="error" className="mb-5">{error}</Alert>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left — account details */}
        <div className="lg:col-span-2 space-y-5">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Account Details</h3>
              <Button variant="outline" size="sm" onClick={() => setEditing(e => !e)}>
                {editing ? 'Cancel' : 'Edit'}
              </Button>
            </div>

            {editing ? (
              <div className="space-y-4">
                <Input label="Full Name" value={name} onChange={e => setName(e.target.value)} />
                <Input label="Email Address" type="email" defaultValue={userEmail} disabled />
                <Input label="National ID" defaultValue="On file" disabled hint="National ID cannot be changed. Contact AXA Egypt to update." />
                <Button onClick={handleSave}>Save Changes</Button>
              </div>
            ) : (
              <>
                <DataRow label="Full name" value={name} />
                <DataRow label="Email" value={userEmail} />
                <DataRow label="National ID" value={<span className="font-mono text-xs">On file</span>} />
                <DataRow label="Account status" value={
                  <span className="text-xs font-semibold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">Active</span>
                } />
                <DataRow label="Member since" value="—" />
              </>
            )}
          </Card>

          {/* Security */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4" style={{ fontFamily: 'var(--font-display)' }}>Security</h3>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">Password</p>
                <p className="text-xs text-gray-400">Last changed 3 months ago</p>
              </div>
              <Button variant="outline" size="sm">Change Password</Button>
            </div>
          </Card>

          {/* Policy summary */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4" style={{ fontFamily: 'var(--font-display)' }}>My Policies Summary</h3>
            <div className="space-y-3">
              {policies.map(p => (
                <div key={p.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">
                      {p.productLine === 'HEALTH' ? '🏥' : p.productLine === 'MOTOR' ? '🚗' : p.productLine === 'PROPERTY' ? '🏠' : '✈️'}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-gray-800">{p.number}</p>
                      <p className="text-xs text-gray-400">{p.productLine} · {p.startDate} → {p.endDate}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    p.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700' :
                    p.status === 'LAPSED' ? 'bg-amber-50 text-amber-700' :
                    'bg-red-50 text-red-700'
                  }`}>{p.status}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right — stats */}
        <div className="space-y-5">
          {/* Avatar / identity */}
          <Card className="p-5 text-center">
            <div className="w-16 h-16 rounded-full bg-axa-blue flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3" style={{ fontFamily: 'var(--font-display)' }}>
              {name.charAt(0)}
            </div>
            <p className="font-bold text-gray-900 text-base">{name}</p>
            <p className="text-xs text-gray-500 mt-0.5">AXA Egypt Customer</p>
            <span className="inline-block mt-2 px-2.5 py-1 bg-axa-blue-50 text-axa-blue text-xs font-semibold rounded-full">
              Verified Account
            </span>
          </Card>

          {/* Claim stats */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4" style={{ fontFamily: 'var(--font-display)' }}>Claims Summary</h3>
            <div className="space-y-3">
              {[
                { label: 'Total claims', value: claims.length },
                { label: 'Approved', value: approvedClaims.length },
                { label: 'Active policies', value: activePolicies.length },
                { label: 'Total approved', value: <Amount value={totalApproved} size="sm" /> },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">{label}</span>
                  <span className="text-sm font-bold text-gray-800">{value}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Contact */}
          <Card className="p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3" style={{ fontFamily: 'var(--font-display)' }}>AXA Egypt Support</h3>
            <div className="space-y-2 text-sm text-gray-600">
              <p>📞 19913</p>
              <p>✉ claims@axa-egypt.com</p>
              <p>🌐 www.axa.com.eg</p>
            </div>
            <p className="text-xs text-gray-400 mt-3">24/7 claims hotline available</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
