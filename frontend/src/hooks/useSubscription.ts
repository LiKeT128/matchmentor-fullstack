import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { Subscription, BillingHistory } from '../types';

interface UseSubscriptionReturn {
    subscription: Subscription | null;
    billingHistory: BillingHistory[];
    loading: boolean;
    error: string | null;
    fetchSubscription: () => Promise<void>;
    fetchBillingHistory: () => Promise<void>;
    createCheckoutSession: (priceId: string) => Promise<string>;
    cancelSubscription: () => Promise<void>;
    resumeSubscription: () => Promise<void>;
}

export const useSubscription = (): UseSubscriptionReturn => {
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [billingHistory, setBillingHistory] = useState<BillingHistory[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchSubscription = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.get<Subscription>('/api/subscription');
            setSubscription(data);
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to fetch subscription');
            setError(message);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchBillingHistory = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await api.get<BillingHistory[]>('/api/subscription/billing-history');
            setBillingHistory(data);
        } catch {
            // Billing history is optional, don't show error
        } finally {
            setLoading(false);
        }
    }, []);

    const createCheckoutSession = useCallback(async (priceId: string): Promise<string> => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.post<{ checkout_url: string }>('/api/subscription/checkout', {
                price_id: priceId,
            });
            return data.checkout_url;
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to create checkout session');
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const cancelSubscription = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            await api.post('/api/subscription/cancel');
            await fetchSubscription();
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to cancel subscription');
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [fetchSubscription]);

    const resumeSubscription = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            await api.post('/api/subscription/resume');
            await fetchSubscription();
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to resume subscription');
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [fetchSubscription]);

    return {
        subscription,
        billingHistory,
        loading,
        error,
        fetchSubscription,
        fetchBillingHistory,
        createCheckoutSession,
        cancelSubscription,
        resumeSubscription,
    };
};

function extractErrorMessage(err: unknown, fallback: string): string {
    if (err && typeof err === 'object' && 'response' in err) {
        const response = (err as { response?: { data?: { detail?: string } } }).response;
        if (response?.data?.detail) {
            return response.data.detail;
        }
    }
    return fallback;
}

export default useSubscription;
