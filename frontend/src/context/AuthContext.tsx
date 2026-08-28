import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, getToken, ApiError } from '../api/client';
import type { Patient } from '../types/api';

interface AuthContextValue {
  isAuthenticated: boolean;
  patient: Patient | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshPatient: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(!!getToken());
  const [loading, setLoading] = useState(!!getToken());
  const [error, setError] = useState<string | null>(null);

  async function refreshPatient() {
    try {
      const p = await api.getMyProfile();
      setPatient(p);
      setIsAuthenticated(true);
    } catch {
      setIsAuthenticated(false);
      setPatient(null);
      api.logout();
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (getToken()) {
      refreshPatient();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    setError(null);
    try {
      await api.login(email, password);
      await refreshPatient();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not sign in. Try again.');
      throw e;
    }
  }

  async function register(email: string, password: string, fullName?: string) {
    setError(null);
    try {
      await api.register(email, password, fullName);
      await login(email, password);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not create your account. Try again.');
      throw e;
    }
  }

  function logout() {
    api.logout();
    setIsAuthenticated(false);
    setPatient(null);
  }

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, patient, loading, error, login, register, logout, refreshPatient }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
