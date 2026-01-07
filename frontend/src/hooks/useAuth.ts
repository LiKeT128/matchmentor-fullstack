import { useState, useCallback } from 'react';
import { api } from '../services/api';
import { storage } from '../services/storage';
import type { AuthResponse, LoginCredentials, RegisterCredentials } from '../types';

interface UseAuthReturn {
    token: string | null;
    loading: boolean;
    error: string | null;
    isAuthenticated: boolean;
    register: (credentials: RegisterCredentials) => Promise<AuthResponse>;
    login: (credentials: LoginCredentials) => Promise<AuthResponse>;
    logout: () => void;
    clearError: () => void;
}

export const useAuth = (): UseAuthReturn => {
    const [token, setToken] = useState<string | null>(storage.getToken());
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const register = useCallback(async (credentials: RegisterCredentials): Promise<AuthResponse> => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.post<AuthResponse>('/api/auth/register', credentials);
            storage.setToken(data.access_token);
            setToken(data.access_token);
            return data;
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Registration failed');
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const login = useCallback(async (credentials: LoginCredentials): Promise<AuthResponse> => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await api.post<AuthResponse>('/api/auth/login', credentials);
            storage.setToken(data.access_token);
            setToken(data.access_token);
            return data;
        } catch (err: unknown) {
            const message = extractErrorMessage(err, 'Login failed');
            setError(message);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const logout = useCallback(() => {
        storage.clearAuth();
        setToken(null);
        setError(null);
    }, []);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    return {
        token,
        loading,
        error,
        isAuthenticated: !!token,
        register,
        login,
        logout,
        clearError,
    };
};

// Helper function to extract error message from API errors
function extractErrorMessage(err: unknown, fallback: string): string {
    if (err && typeof err === 'object' && 'response' in err) {
        const response = (err as { response?: { data?: { detail?: string } } }).response;
        if (response?.data?.detail) {
            return response.data.detail;
        }
    }
    return fallback;
}

export default useAuth;
