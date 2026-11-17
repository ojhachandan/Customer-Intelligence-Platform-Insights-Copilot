import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  authService,
  type LoginCredentials,
  type SignUpData,
  type UserProfile,
} from "../services/authService";

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<UserProfile>;
  signup: (data: SignUpData) => Promise<UserProfile>;
  logout: () => Promise<void>;
  updateProfile: (updates: Partial<UserProfile>) => Promise<UserProfile>;
  changePassword: (oldPass: string, newPass: string) => Promise<void>;
  deleteAccount: (confirmEmail: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(() => authService.getCurrentUser());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Validate session on mount
    const current = authService.getCurrentUser();
    setUser(current);
    setIsLoading(false);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const loggedIn = await authService.login(credentials);
      setUser(loggedIn);
      return loggedIn;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (data: SignUpData) => {
    setIsLoading(true);
    try {
      const newUser = await authService.signup(data);
      setUser(newUser);
      return newUser;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authService.logout();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const updateProfile = async (updates: Partial<UserProfile>) => {
    const updated = await authService.updateProfile(updates);
    setUser(updated);
    return updated;
  };

  const changePassword = async (oldPass: string, newPass: string) => {
    await authService.changePassword(oldPass, newPass);
  };

  const deleteAccount = async (confirmEmail: string) => {
    await authService.deleteAccount(confirmEmail);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
        updateProfile,
        changePassword,
        deleteAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

