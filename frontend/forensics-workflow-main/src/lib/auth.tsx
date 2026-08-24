import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

const STORAGE_KEY = "eed.session";

export interface SessionUser {
  email: string;
  name: string;
  role: string;
}

interface AuthState {
  user: SessionUser | null;
  hydrated: boolean;
  login: (email: string, password: string, remember: boolean) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const nameFromEmail = (email: string) => {
  const base = (email.split("@")[0] ?? "").replace(/[._-]+/g, " ").trim();
  return base
    .split(" ")
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ") || "Investigator";
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw =
        window.localStorage.getItem(STORAGE_KEY) ?? window.sessionStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw) as SessionUser);
    } catch {
      /* ignore corrupt session */
    }
    setHydrated(true);
  }, []);

  const login = useCallback(async (email: string, password: string, remember: boolean) => {
    // Frontend-only mock authentication. No backend, no network call.
    await new Promise((r) => setTimeout(r, 550));
    if (password.length < 6) {
      throw new Error("Invalid credentials. Password must be at least 6 characters.");
    }
    const session: SessionUser = {
      email,
      name: nameFromEmail(email),
      role: "Forensic Examiner",
    };
    const store = remember ? window.localStorage : window.sessionStorage;
    store.setItem(STORAGE_KEY, JSON.stringify(session));
    (remember ? window.sessionStorage : window.localStorage).removeItem(STORAGE_KEY);
    setUser(session);
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    window.sessionStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, hydrated, login, logout }),
    [user, hydrated, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
