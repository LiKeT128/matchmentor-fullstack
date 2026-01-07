import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { Coach } from '../types';

interface UseCoachesReturn {
    coaches: Coach[];
    loading: boolean;
    error: string | null;
    fetchCoaches: (filters?: CoachFilters) => Promise<void>;
    clearError: () => void;
}

interface CoachFilters {
    specialization?: string;
    minRating?: number;
    maxRate?: number;
    available?: boolean;
}

export const useCoaches = (): UseCoachesReturn => {
    const [coaches, setCoaches] = useState<Coach[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchCoaches = useCallback(async (filters?: CoachFilters): Promise<void> => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            if (filters?.specialization) params.append('specialization', filters.specialization);
            if (filters?.minRating) params.append('min_rating', filters.minRating.toString());
            if (filters?.maxRate) params.append('max_rate', filters.maxRate.toString());
            if (filters?.available !== undefined) params.append('available', filters.available.toString());

            const { data } = await api.get<Coach[]>(`/api/coaches?${params.toString()}`);
            setCoaches(data);
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to fetch coaches');
            setError(message);
        } finally {
            setLoading(false);
        }
    }, []);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        coaches,
        loading,
        error,
        fetchCoaches,
        clearError,
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

export default useCoaches;
