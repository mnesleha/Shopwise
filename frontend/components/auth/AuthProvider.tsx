"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "@/lib/api";

type AuthState = {
  isAuthenticated: boolean;
  email?: string;
  refresh: () => Promise<void>;
  setAnonymous: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [email, setEmail] = useState<string | undefined>(undefined);

  const refresh = useCallback(async () => {
    const res = await api.get("/auth/me/");
    const data = res.data as { is_authenticated: boolean; email?: string };
    setIsAuthenticated(Boolean(data.is_authenticated));
    setEmail(data.email);
  }, []);

  const setAnonymous = useCallback(() => {
    setIsAuthenticated(false);
    setEmail(undefined);
  }, []);

  useEffect(() => {
    // initial load
    refresh().catch(() => setAnonymous());
  }, [refresh, setAnonymous]);

  const value = useMemo(
    () => ({ isAuthenticated, email, refresh, setAnonymous }),
    [isAuthenticated, email, refresh, setAnonymous],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
