/**
 * ============================================================================
 * AUTHENTICATION SERVICE (DEV / CLIENT PERSISTED MOCK)
 * ============================================================================
 * IMPORTANT SECURITY NOTICE:
 * This client-side authentication service stores session metadata in browser
 * localStorage for development and evaluation purposes. In a production enterprise
 * deployment, passwords MUST NEVER be processed or stored in plain-text on the client.
 * Authentication should always terminate at a secure backend using HTTP-only,
 * Secure, SameSite cookies with bcrypt/argon2 password hashing and signed JWT/OAuth2 tokens.
 * ============================================================================
 */

export interface UserPreferences {
  theme: "light" | "dark" | "system";
  emailAlerts: boolean;
  weeklyDigest: boolean;
  reducedMotion: boolean;
  density: "comfortable" | "compact";
}

export interface UserSession {
  id: string;
  device: string;
  location: string;
  lastActive: string;
  isCurrent: boolean;
}

export interface UserProfile {
  id: string;
  name: string;
  firstName: string;
  lastName: string;
  email: string;
  avatar?: string;
  phone?: string;
  jobTitle?: string;
  company?: string;
  location?: string;
  timezone?: string;
  bio?: string;
  memberSince: string;
  lastLogin: string;
  preferences: UserPreferences;
  sessions: UserSession[];
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface SignUpData {
  fullName: string;
  email: string;
  password: string;
}

const STORAGE_USER_KEY = "the_qasar_auth_current_user";
const STORAGE_TOKEN_KEY = "the_qasar_auth_token";

// One-time key migration from legacy storage keys
try {
  if (typeof window !== "undefined") {
    const legacyUser = localStorage.getItem("cip_auth_current_user");
    if (legacyUser !== null && localStorage.getItem(STORAGE_USER_KEY) === null) {
      localStorage.setItem(STORAGE_USER_KEY, legacyUser);
    }
    const legacyToken = localStorage.getItem("cip_auth_token");
    if (legacyToken !== null && localStorage.getItem(STORAGE_TOKEN_KEY) === null) {
      localStorage.setItem(STORAGE_TOKEN_KEY, legacyToken);
    }
  }
} catch {
  /* ignore */
}

const DEFAULT_USER: UserProfile = {
  id: "usr_01hq7",
  name: "Alex Rivera",
  firstName: "Alex",
  lastName: "Rivera",
  email: "director@company.com",
  avatar: "",
  phone: "+1 (555) 234-5678",
  jobTitle: "Analytics Director",
  company: "The Qasar Enterprise SaaS",
  location: "San Francisco, CA",
  timezone: "America/Los_Angeles (UTC-7)",
  bio: "Lead enterprise business intelligence and consumer segmentation workflows across our omnichannel commerce network.",
  memberSince: "March 2024",
  lastLogin: "Just now",
  preferences: {
    theme: "light",
    emailAlerts: true,
    weeklyDigest: true,
    reducedMotion: false,
    density: "comfortable",
  },
  sessions: [
    {
      id: "sess_1",
      device: "MacBook Pro 16″ (Chrome 128)",
      location: "San Francisco, US",
      lastActive: "Active now",
      isCurrent: true,
    },
    {
      id: "sess_2",
      device: "iPhone 15 Pro (Safari Mobile)",
      location: "San Francisco, US",
      lastActive: "2 hours ago",
      isCurrent: false,
    },
  ],
};

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class AuthService {
  private currentUser: UserProfile | null = null;

  constructor() {
    this.init();
  }

  private init() {
    try {
      const saved = localStorage.getItem(STORAGE_USER_KEY);
      const token = localStorage.getItem(STORAGE_TOKEN_KEY);
      if (saved && token) {
        this.currentUser = JSON.parse(saved);
      }
    } catch {
      this.currentUser = null;
    }
  }

  public getCurrentUser(): UserProfile | null {
    return this.currentUser;
  }

  public isAuthenticated(): boolean {
    return this.currentUser !== null;
  }

  public async login(credentials: LoginCredentials): Promise<UserProfile> {
    await delay(600); // Simulate network latency

    if (!credentials.email || !credentials.password) {
      throw new Error("Please enter both email and password.");
    }

    // Accept valid demo credentials or existing user
    let user = this.currentUser;
    if (!user || user.email.toLowerCase() !== credentials.email.toLowerCase()) {
      const [first, ...rest] = credentials.email.split("@")[0].split(".");
      const firstName = first ? first.charAt(0).toUpperCase() + first.slice(1) : "User";
      const lastName = rest.length ? rest.join(" ").charAt(0).toUpperCase() + rest.join(" ").slice(1) : "";
      const name = `${firstName} ${lastName}`.trim();

      user = {
        ...DEFAULT_USER,
        id: `usr_${Math.random().toString(36).substring(2, 8)}`,
        email: credentials.email,
        name: name || "Enterprise Analyst",
        firstName: firstName || "Enterprise",
        lastName: lastName || "Analyst",
        lastLogin: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
    } else {
      user.lastLogin = "Just now";
    }

    this.currentUser = user;
    try {
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
      localStorage.setItem(STORAGE_TOKEN_KEY, `mock_jwt_${Date.now()}`);
    } catch {
      /* ignore */
    }

    return user;
  }

  public async signup(data: SignUpData): Promise<UserProfile> {
    await delay(700);

    const parts = data.fullName.trim().split(" ");
    const firstName = parts[0] || "User";
    const lastName = parts.slice(1).join(" ") || "";

    const user: UserProfile = {
      ...DEFAULT_USER,
      id: `usr_${Math.random().toString(36).substring(2, 8)}`,
      email: data.email,
      name: data.fullName,
      firstName,
      lastName,
      memberSince: new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" }),
      lastLogin: "Just now",
    };

    this.currentUser = user;
    try {
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
      localStorage.setItem(STORAGE_TOKEN_KEY, `mock_jwt_${Date.now()}`);
    } catch {
      /* ignore */
    }

    return user;
  }

  public async logout(): Promise<void> {
    await delay(300);
    this.currentUser = null;
    try {
      localStorage.removeItem(STORAGE_USER_KEY);
      localStorage.removeItem(STORAGE_TOKEN_KEY);
    } catch {
      /* ignore */
    }
  }

  public async updateProfile(updates: Partial<UserProfile>): Promise<UserProfile> {
    await delay(400);
    if (!this.currentUser) throw new Error("Not authenticated");

    const updated: UserProfile = {
      ...this.currentUser,
      ...updates,
      firstName: updates.name ? updates.name.split(" ")[0] || this.currentUser.firstName : this.currentUser.firstName,
      lastName: updates.name ? updates.name.split(" ").slice(1).join(" ") || this.currentUser.lastName : this.currentUser.lastName,
    };

    this.currentUser = updated;
    try {
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(updated));
    } catch {
      /* ignore */
    }

    return updated;
  }

  public async changePassword(oldPass: string, newPass: string): Promise<void> {
    await delay(600);
    if (!oldPass || !newPass) throw new Error("Please fill out all password fields.");
    if (newPass.length < 8) throw new Error("New password must be at least 8 characters long.");
    // In production, backend validates old password hash and updates bcrypt hash
  }

  public async deleteAccount(confirmEmail: string): Promise<void> {
    await delay(600);
    if (!this.currentUser || confirmEmail.toLowerCase() !== this.currentUser.email.toLowerCase()) {
      throw new Error("Confirmation email does not match your account email.");
    }
    await this.logout();
  }
}

export const authService = new AuthService();

