import { useEffect, useState } from 'react';
import { getMyClaims, getMyPolicies } from '../api';
import type { Claim, Policy } from '../types';

export function useCustomerData(token: string) {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    Promise.all([getMyPolicies(token), getMyClaims(token)])
      .then(([nextPolicies, nextClaims]) => {
        if (!active) return;
        setPolicies(nextPolicies);
        setClaims(nextClaims);
      })
      .catch(requestError => {
        if (!active) return;
        setPolicies([]);
        setClaims([]);
        setError(requestError instanceof Error ? requestError.message : 'Unable to load your account data.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  return { policies, claims, loading, error };
}
