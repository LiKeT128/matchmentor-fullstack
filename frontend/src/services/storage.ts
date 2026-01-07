const TOKEN_KEY = 'token';
const USER_KEY = 'user';

export const storage = {
    // Token management
    getToken: (): string | null => {
        return localStorage.getItem(TOKEN_KEY);
    },

    setToken: (token: string): void => {
        localStorage.setItem(TOKEN_KEY, token);
    },

    removeToken: (): void => {
        localStorage.removeItem(TOKEN_KEY);
    },

    // User data management
    getUser: <T>(): T | null => {
        const user = localStorage.getItem(USER_KEY);
        if (user) {
            try {
                return JSON.parse(user) as T;
            } catch {
                return null;
            }
        }
        return null;
    },

    setUser: <T>(user: T): void => {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    removeUser: (): void => {
        localStorage.removeItem(USER_KEY);
    },

    // Clear all auth data
    clearAuth: (): void => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },

    // Check if user is authenticated
    isAuthenticated: (): boolean => {
        return !!localStorage.getItem(TOKEN_KEY);
    },
};

export default storage;
