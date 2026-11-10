"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiJson } from "@/lib/api";

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface LoginResult {
  ok: boolean;
  mfaRequired?: boolean;
  error?: string;
}

interface AuthContextType {
  token: string | null;
  login: (email: string, password: string) => Promise<LoginResult>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("anomaly_token");
    setToken(stored);
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<LoginResult> => {
    try {
      const data = await apiJson<AuthTokens & { mfa_required?: boolean; access_token?: string | null; refresh_token?: string | null }>(
        "/api/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }
      );
      if (data.mfa_required) {
        return { ok: false, mfaRequired: true, error: "Multi-factor authentication is required for this account." };
      }
      if (data.access_token) {
        setToken(data.access_token);
        localStorage.setItem("anomaly_token", data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("anomaly_refresh_token", data.refresh_token);
        }
        return { ok: true };
      }
      return { ok: false, error: "Login response did not include an access token." };
    } catch (err) {
      console.error("Login failed:", err);
      return { ok: false, error: err instanceof Error ? err.message : "Login failed." };
    }
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem("anomaly_token");
    localStorage.removeItem("anomaly_refresh_token");
  };

  return (
    <AuthContext.Provider
      value={{ token, login, logout, isAuthenticated: !!token, isLoading }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
