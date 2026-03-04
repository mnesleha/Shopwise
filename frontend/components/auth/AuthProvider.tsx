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
  firstName?: string;
  lastName?: string;
  refresh: () => Promise<{ isAuthenticated: boolean; email?: string }>;
  setAnonymous: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({
  children,
  initialIsAuthenticated = false,
  initialEmail,
}: {
  children: React.ReactNode;
  initialIsAuthenticated?: boolean;
  initialEmail?: string;
}) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    initialIsAuthenticated,
  );
  const [email, setEmail] = useState<string | undefined>(initialEmail);
  const [firstName, setFirstName] = useState<string | undefined>(undefined);
  const [lastName, setLastName] = useState<string | undefined>(undefined);

  const refresh = useCallback(async () => {
    const res = await api.get("/auth/me/");
    const data = res.data as {
      is_authenticated: boolean;
      email?: string;
      first_name?: string;
      last_name?: string;
    };
    const isAuth = Boolean(data.is_authenticated);
    setIsAuthenticated(isAuth);
    setEmail(data.email);
    setFirstName(data.first_name);
    setLastName(data.last_name);
    return { isAuthenticated: isAuth, email: data.email };
  }, []);

  const setAnonymous = useCallback(() => {
    setIsAuthenticated(false);
    setEmail(undefined);
    setFirstName(undefined);
    setLastName(undefined);
  }, []);

  useEffect(() => {
    // initial load
    refresh().catch(() => setAnonymous());
  }, [refresh, setAnonymous]);

  const value = useMemo(
    () => ({
      isAuthenticated,
      email,
      firstName,
      lastName,
      refresh,
      setAnonymous,
    }),
    [isAuthenticated, email, firstName, lastName, refresh, setAnonymous],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
