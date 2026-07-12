import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { authApi } from "@/api/endpoints";
import { setStoredTokens, clearStoredTokens } from "@/api/client";
import type { User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const hasToken = !!localStorage.getItem("rentaliq_access_token");
    if (!hasToken) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => clearStoredTokens())
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    setStoredTokens(response.access_token, response.refresh_token);
    setUser(response.user);
  };

  const logout = () => {
    clearStoredTokens();
    setUser(null);
    window.location.href = "/login";
  };

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
