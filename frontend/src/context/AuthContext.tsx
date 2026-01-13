import React, { createContext, useState, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import { api } from '../services/api';
import { storage } from '../services/storage';
import type { AuthResponse, LoginCredentials, RegisterCredentials } from '../types';

interface AuthContextType {
    token: string | null;
    loading: boolean;
    error: string | null;
    isAuthenticated: boolean;
    register: (credentials: RegisterCredentials) => Promise<AuthResponse>;
    login: (credentials: LoginCredentials) => Promise<AuthResponse>;
    logout: () => void;
    clearError: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    // Initialize from storage
    const [token, setToken] = useState<string | null>(storage.getToken());
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Sync state with storage on mount (in case it changed externally, though unlikely in SPA)
    useEffect(() => {
        const storedToken = storage.getToken();
        if (storedToken !== token) {
            setToken(storedToken);
        }
    }, []);

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

    const value = {
        token,
        loading,
        error,
        isAuthenticated: !!token,
        register,
        login,
        logout,
        clearError,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
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
