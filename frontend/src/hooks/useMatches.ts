import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { Match, MatchAnalysis, UploadResponse } from '../types';

interface UseMatchesReturn {
    matches: Match[];
    currentAnalysis: MatchAnalysis | null;
    loading: boolean;
    uploading: boolean;
    uploadProgress: number;
    error: string | null;
    fetchMatches: () => Promise<void>;
    fetchAnalysis: (matchId: string) => Promise<MatchAnalysis>;
    uploadReplay: (file: File) => Promise<UploadResponse>;
    clearError: () => void;
}

export const useMatches = (): UseMatchesReturn => {
    const [matches, setMatches] = useState<Match[]>([]);
    const [currentAnalysis, setCurrentAnalysis] = useState<MatchAnalysis | null>(null);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);

    const fetchMatches = useCallback(async (): Promise<void> => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.get<Match[]>('/api/matches');
            setMatches(data);
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to fetch matches');
            setError(message);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchAnalysis = useCallback(async (matchId: string): Promise<MatchAnalysis> => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.get<MatchAnalysis>(`/api/matches/${matchId}/analysis`);
            setCurrentAnalysis(data);
            return data;
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to fetch analysis');
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const uploadReplay = useCallback(async (file: File): Promise<UploadResponse> => {
        setUploading(true);
        setUploadProgress(0);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const { data } = await api.post<UploadResponse>('/api/matches/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total) {
                        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setUploadProgress(progress);
                    }
                },
            });
            return data;
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Failed to upload replay');
            setError(message);
            throw err;
        } finally {
            setUploading(false);
        }
    }, []);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        matches,
        currentAnalysis,
        loading,
        uploading,
        uploadProgress,
        error,
        fetchMatches,
        fetchAnalysis,
        uploadReplay,
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

export default useMatches;
