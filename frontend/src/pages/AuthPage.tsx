import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  Eye,
  EyeOff,
  Github,
  Lock,
  Mail,
  Sparkles,
  TrendingUp,
  User,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { PasswordStrengthMeter } from "../components/auth/PasswordStrengthMeter";
import { formatINR } from "../lib/formatCurrency";
import { usdToInr } from "../config/currency";

const loginSchema = z.object({
  email: z.string().email("Please enter a valid work email address"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean().optional(),
});

const signupSchema = z
  .object({
    fullName: z.string().min(2, "Full name must be at least 2 characters"),
    email: z.string().email("Please enter a valid work email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Include at least one uppercase letter")
      .regex(/[0-9]/, "Include at least one number"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
    agreeToTerms: z.literal(true, {
      errorMap: () => ({ message: "You must agree to the Terms & Privacy Policy" }),
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type LoginFormValues = z.infer<typeof loginSchema>;
type SignupFormValues = z.infer<typeof signupSchema>;

const VALUE_PROPS = [
  "Autonomous RFM Behavioral Segmentation",
  "Implicit ALS Collaborative Recommenders",
  "Grounded AI Insights Copilot with Real-time Citations",
  "Feature Distribution Drift & Automated PSI Tracking",
];

const HEADLINE_WORDS = ["Understand", "every", "customer."];

export default function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login, signup, isAuthenticated } = useAuth();

  // Mode: login or signup. Check pathname (/login or /signup or default /auth)
  const initialMode = location.pathname === "/signup" ? "signup" : "login";
  const [mode, setMode] = useState<"login" | "signup">(initialMode);

  // Sync mode with route if navigating
  useEffect(() => {
    if (location.pathname === "/signup") setMode("signup");
    else if (location.pathname === "/login") setMode("login");
  }, [location.pathname]);

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [successName, setSuccessName] = useState<string | null>(null);
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSubmitted, setForgotSubmitted] = useState(false);
  const [valuePropIndex, setValuePropIndex] = useState(0);

  // Redirect target
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  useEffect(() => {
    if (isAuthenticated && !successName) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, successName, navigate]);

  // Rotating value prop cycle
  useEffect(() => {
    const timer = setInterval(() => {
      setValuePropIndex((prev) => (prev + 1) % VALUE_PROPS.length);
    }, 3600);
    return () => clearInterval(timer);
  }, []);

  // React Hook Form setups
  const {
    register: registerLogin,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors, isSubmitting: isLoginSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "director@company.com", password: "Password123!", rememberMe: true },
  });

  const {
    register: registerSignup,
    handleSubmit: handleSignupSubmit,
    watch: watchSignup,
    formState: { errors: signupErrors, isSubmitting: isSignupSubmitting },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: "", email: "", password: "", confirmPassword: "" },
  });

  const signupPassword = watchSignup("password") || "";

  const onLogin = async (data: LoginFormValues) => {
    setAuthError(null);
    try {
      const user = await login(data);
      setSuccessName(user.firstName);
      setTimeout(() => {
        navigate(from, { replace: true });
      }, 1200);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Invalid email or password");
    }
  };

  const onSignup = async (data: SignupFormValues) => {
    setAuthError(null);
    try {
      const user = await signup({
        fullName: data.fullName,
        email: data.email,
        password: data.password,
      });
      setSuccessName(user.firstName);
      setTimeout(() => {
        navigate(from, { replace: true });
      }, 1200);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Failed to create account");
    }
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[var(--bg-page)] text-[var(--text-primary)] flex flex-col lg:flex-row">
      {/* Background Soft Mesh Blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -left-32 h-[500px] w-[500px] rounded-full bg-[#2DD4BF]/12 blur-[120px]" />
        <div className="absolute top-1/2 -right-32 h-[450px] w-[450px] rounded-full bg-[#D4A24C]/10 blur-[130px]" />
        <div className="absolute -bottom-32 left-1/3 h-[400px] w-[400px] rounded-full bg-[#5B7FA6]/8 blur-[110px]" />
      </div>

      {/* LEFT PANEL: Brand, Vision, Floating Preview (Desktop ~50%) */}
      <div className="relative hidden lg:flex lg:w-1/2 flex-col justify-between p-12 xl:p-16 border-r border-[var(--border-subtle)] bg-[var(--bg-subtle)]/40 backdrop-blur-xs">
        {/* Brand header */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[12px] bg-[var(--accent)] font-serif font-bold text-[var(--on-accent)] shadow-soft">
            <span className="text-lg">CI</span>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="rounded-[4px] bg-[var(--accent-soft)] px-1.5 py-0.2 font-mono text-[9px] font-bold tracking-widest text-[var(--accent)] border border-[var(--accent-border)]">
                THE QASAR
              </span>
            </div>
            <p className="heading-serif text-sm font-semibold tracking-tight text-[var(--text-primary)]">
              Customer Intelligence
            </p>
          </div>
        </div>

        {/* Hero Narrative with Word-by-Word Reveal */}
        <div className="my-auto space-y-6 max-w-xl">
          <div className="overflow-hidden">
            <h1 className="heading-serif text-4xl xl:text-5xl font-medium tracking-tight text-[var(--text-primary)] leading-[1.15]">
              {HEADLINE_WORDS.map((word, idx) => (
                <motion.span
                  key={idx}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: idx * 0.12, ease: "easeOut" }}
                  className="inline-block mr-3"
                >
                  {word}
                </motion.span>
              ))}
            </h1>
          </div>

          <div className="h-12 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.p
                key={valuePropIndex}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -14 }}
                transition={{ duration: 0.35, ease: "easeInOut" }}
                className="text-base text-[var(--text-secondary)] font-normal leading-relaxed"
              >
                {VALUE_PROPS[valuePropIndex]}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Floating Interactive Mini-Dashboard Preview */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4, ease: "easeOut" }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className="rounded-[20px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-elevated"
          >
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#84CC16] animate-ping" />
                <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Live Warehouse Synthesis
                </span>
              </div>
              <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 font-mono text-[10px] text-[var(--accent)] font-semibold border border-[var(--accent-border)]">
                v1.2 Active
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3">
                <p className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">Total Revenue</p>
                <p className="mt-1 heading-serif text-lg font-bold text-[var(--text-primary)]">{formatINR(usdToInr(284950))}</p>
                <span className="text-[10px] text-[#84CC16] font-semibold flex items-center gap-0.5 mt-0.5">
                  <TrendingUp size={11} /> +18.4% this quarter
                </span>
              </div>
              <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3">
                <p className="text-[10px] uppercase font-semibold text-[var(--text-muted)]">Active Clusters</p>
                <p className="mt-1 heading-serif text-lg font-bold text-[var(--text-primary)]">4 Segments</p>
                <span className="text-[10px] text-[var(--accent)] font-semibold flex items-center gap-0.5 mt-0.5">
                  <Sparkles size={11} /> High monetary affinity
                </span>
              </div>
            </div>

            {/* Drawing SVG Line Curve */}
            <div className="rounded-[14px] border border-[var(--border-subtle)] bg-[var(--bg-subtle)]/50 p-3">
              <div className="flex justify-between text-[11px] text-[var(--text-muted)] mb-2">
                <span>Revenue Trajectory</span>
                <span className="font-mono text-[var(--accent)] font-medium">Healthy</span>
              </div>
              <svg className="w-full h-12 overflow-visible" viewBox="0 0 240 50">
                <defs>
                  <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#2DD4BF" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <motion.path
                  d="M 0 45 Q 40 38, 80 25 T 160 20 T 240 5"
                  fill="none"
                  stroke="#2DD4BF"
                  strokeWidth="2.5"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 1.2, ease: "easeInOut" }}
                />
              </svg>
            </div>
          </motion.div>
        </div>

        {/* Footer info */}
        <div className="text-xs text-[var(--text-muted)] flex items-center justify-between">
          <span>Enterprise Grade SaaS Intelligence</span>
          <span>© 2026 The Qasar Platform</span>
        </div>
      </div>

      {/* RIGHT PANEL: Form (50% on Desktop, 100% on Mobile) */}
      <div className="relative flex-1 flex flex-col justify-center items-center p-6 sm:p-10 lg:p-16">
        {/* Mobile Header */}
        <div className="mb-6 flex lg:hidden items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[var(--accent)] font-serif font-bold text-[var(--on-accent)] shadow-soft">
            CI
          </div>
          <div>
            <span className="rounded bg-[var(--accent-soft)] px-1.5 py-0.2 font-mono text-[9px] font-bold tracking-widest text-[var(--accent)] border border-[var(--accent-border)]">
              THE QASAR
            </span>
            <p className="heading-serif text-sm font-semibold text-[var(--text-primary)]">
              Customer Intelligence
            </p>
          </div>
        </div>

        {/* Success Splash Greeting Overlay */}
        <AnimatePresence>
          {successName && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[var(--bg-page)]/95 p-8 text-center backdrop-blur-md"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="flex h-16 w-16 items-center justify-center rounded-full bg-[#84CC16] text-[#12141C] shadow-glow mb-4"
              >
                <Check size={32} strokeWidth={2.5} />
              </motion.div>
              <h2 className="heading-serif text-2xl font-bold text-[var(--text-primary)]">
                Welcome back, {successName}
              </h2>
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                Loading your intelligence workspace…
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Form Container Card */}
        <motion.div
          animate={authError ? { x: [-6, 6, -4, 4, 0] } : {}}
          transition={{ duration: 0.3 }}
          className="w-full max-w-md rounded-[24px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 sm:p-8 shadow-elevated"
        >
          {/* Animated Tab Switcher */}
          <div className="relative mb-6 grid grid-cols-2 rounded-[14px] bg-[var(--bg-subtle)] p-1 border border-[var(--border-subtle)]">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setAuthError(null);
              }}
              className={`relative z-10 flex items-center justify-center py-2 text-xs font-semibold bg-transparent transition-colors duration-150 ${
                mode === "login"
                  ? "text-[var(--text-primary)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              }`}
            >
              <span className="relative z-10">Sign In</span>
              {mode === "login" && (
                <motion.div
                  layoutId="auth-tab-indicator"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  className="absolute inset-0 rounded-[10px] bg-[#30302E] shadow-soft border border-[var(--border-subtle)]"
                />
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setMode("signup");
                setAuthError(null);
              }}
              className={`relative z-10 flex items-center justify-center py-2 text-xs font-semibold bg-transparent transition-colors duration-150 ${
                mode === "signup"
                  ? "text-[var(--text-primary)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              }`}
            >
              <span className="relative z-10">Create Account</span>
              {mode === "signup" && (
                <motion.div
                  layoutId="auth-tab-indicator"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  className="absolute inset-0 rounded-[10px] bg-[#30302E] shadow-soft border border-[var(--border-subtle)]"
                />
              )}
            </button>
          </div>

          {/* Error Banner */}
          {authError && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-5 rounded-[12px] border border-[#C4554D]/30 bg-[#C4554D]/10 p-3 text-xs text-[#C4554D] flex items-center gap-2"
            >
              <span>{authError}</span>
            </motion.div>
          )}

          {/* LOGIN FORM */}
          {mode === "login" && (
            <form onSubmit={handleLoginSubmit(onLogin)} className="space-y-4">
              <div>
                <label className="label block mb-1.5" htmlFor="login-email">
                  Work Email
                </label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    placeholder="director@company.com"
                    {...registerLogin("email")}
                    className="input w-full pl-10"
                  />
                </div>
                {loginErrors.email && (
                  <p className="mt-1 text-[11px] text-[#C4554D]">{loginErrors.email.message}</p>
                )}
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="label" htmlFor="login-password">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setForgotModalOpen(true)}
                    className="text-[11px] text-[var(--accent)] hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••••••"
                    {...registerLogin("password")}
                    className="input w-full pl-10 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {loginErrors.password && (
                  <p className="mt-1 text-[11px] text-[#C4554D]">{loginErrors.password.message}</p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <input
                  id="remember-me"
                  type="checkbox"
                  {...registerLogin("rememberMe")}
                  style={{ accentColor: "var(--accent)" }}
                  className="h-4 w-4 rounded border-[var(--border-subtle)] text-[var(--accent)] accent-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <label htmlFor="remember-me" className="text-xs text-[var(--text-secondary)]">
                  Remember this device for 30 days
                </label>
              </div>

              <button
                type="submit"
                disabled={isLoginSubmitting}
                className="btn-primary w-full py-2.5 text-sm font-semibold mt-2"
              >
                {isLoginSubmitting ? (
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Signing in…</span>
                  </div>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    Sign In <ArrowRight size={15} />
                  </span>
                )}
              </button>
            </form>
          )}

          {/* SIGNUP FORM */}
          {mode === "signup" && (
            <form onSubmit={handleSignupSubmit(onSignup)} className="space-y-4">
              <div>
                <label className="label block mb-1.5" htmlFor="signup-name">
                  Full Name
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    id="signup-name"
                    type="text"
                    autoComplete="name"
                    placeholder="Alex Rivera"
                    {...registerSignup("fullName")}
                    className="input w-full pl-10"
                  />
                </div>
                {signupErrors.fullName && (
                  <p className="mt-1 text-[11px] text-[#C4554D]">{signupErrors.fullName.message}</p>
                )}
              </div>

              <div>
                <label className="label block mb-1.5" htmlFor="signup-email">
                  Work Email
                </label>
                <div className="relative">
                  <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    id="signup-email"
                    type="email"
                    autoComplete="email"
                    placeholder="name@company.com"
                    {...registerSignup("email")}
                    className="input w-full pl-10"
                  />
                </div>
                {signupErrors.email && (
                  <p className="mt-1 text-[11px] text-[#C4554D]">{signupErrors.email.message}</p>
                )}
              </div>

              <div>
                <label className="label block mb-1.5" htmlFor="signup-password">
                  Password
                </label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    id="signup-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="••••••••••••"
                    {...registerSignup("password")}
                    className="input w-full pl-10 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <PasswordStrengthMeter password={signupPassword} />
                {signupErrors.password && (
                  <p className="mt-1 text-[11px] text-[#C4554D]">{signupErrors.password.message}</p>
                )}
              </div>

              <div>
                <label className="label block mb-1.5" htmlFor="signup-confirm-password">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                  <input
                    id="signup-confirm-password"
                    type={showConfirmPassword ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="••••••••••••"
                    {...registerSignup("confirmPassword")}
                    className="input w-full pl-10 pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {signupErrors.confirmPassword && (
                  <p className="mt-1 text-[11px] text-[#C4554D]">{signupErrors.confirmPassword.message}</p>
                )}
              </div>

              <div className="flex items-start gap-2">
                <input
                  id="agree-terms"
                  type="checkbox"
                  {...registerSignup("agreeToTerms")}
                  style={{ accentColor: "var(--accent)" }}
                  className="mt-1 h-4 w-4 rounded border-[var(--border-subtle)] text-[var(--accent)] accent-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <label htmlFor="agree-terms" className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  I agree to the{" "}
                  <a href="#" className="text-[var(--accent)] underline">
                    Terms of Service
                  </a>{" "}
                  and{" "}
                  <a href="#" className="text-[var(--accent)] underline">
                    Privacy Policy
                  </a>
                  .
                </label>
              </div>
              {signupErrors.agreeToTerms && (
                <p className="text-[11px] text-[#C4554D]">{signupErrors.agreeToTerms.message}</p>
              )}

              <button
                type="submit"
                disabled={isSignupSubmitting}
                className="btn-primary w-full py-2.5 text-sm font-semibold mt-2"
              >
                {isSignupSubmitting ? (
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Creating account…</span>
                  </div>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    Create Enterprise Account <ArrowRight size={15} />
                  </span>
                )}
              </button>
            </form>
          )}

          {/* Social Sign-In Placeholders */}
          <div className="mt-6 border-t border-[var(--border-subtle)] pt-5">
            <p className="text-center text-[11px] uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Or continue with SSO
            </p>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setAuthError("Google Enterprise SSO is coming soon for your organization domain.")}
                className="btn-secondary py-2 text-xs flex items-center justify-center gap-2"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Google</span>
                <span className="text-[9px] text-[var(--text-muted)] bg-[var(--bg-subtle)] px-1 rounded">Soon</span>
              </button>

              <button
                type="button"
                onClick={() => setAuthError("GitHub OAuth is coming soon for developer instances.")}
                className="btn-secondary py-2 text-xs flex items-center justify-center gap-2"
              >
                <Github size={15} />
                <span>GitHub</span>
                <span className="text-[9px] text-[var(--text-muted)] bg-[var(--bg-subtle)] px-1 rounded">Soon</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Forgot Password Modal */}
      <AnimatePresence>
        {forgotModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-xs"
              onClick={() => {
                setForgotModalOpen(false);
                setForgotSubmitted(false);
              }}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              className="relative w-full max-w-sm rounded-[20px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-elevated"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="heading-serif text-lg font-semibold text-[var(--text-primary)]">
                  Reset Password
                </h3>
                <button
                  type="button"
                  onClick={() => {
                    setForgotModalOpen(false);
                    setForgotSubmitted(false);
                  }}
                  className="rounded-full p-1 text-[var(--text-muted)] hover:bg-[var(--bg-subtle)]"
                >
                  <X size={16} />
                </button>
              </div>

              {forgotSubmitted ? (
                <div className="text-center py-4 space-y-3">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#84CC16]/15 text-[#84CC16]">
                    <CheckCircle2 size={24} />
                  </div>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    Password Reset Link Sent
                  </p>
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                    If an account exists for <strong className="text-[var(--text-primary)]">{forgotEmail}</strong>, instructions to reset your password have been dispatched.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setForgotModalOpen(false);
                      setForgotSubmitted(false);
                    }}
                    className="btn-secondary w-full text-xs mt-3"
                  >
                    Done
                  </button>
                </div>
              ) : (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (forgotEmail) setForgotSubmitted(true);
                  }}
                  className="space-y-4"
                >
                  <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                    Enter your registered account email and we&apos;ll send you a recovery link to reset your credentials.
                  </p>
                  <div>
                    <label className="label block mb-1">Email Address</label>
                    <input
                      type="email"
                      required
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="director@company.com"
                      className="input w-full"
                    />
                  </div>
                  <button type="submit" className="btn-primary w-full text-xs py-2.5">
                    Send Recovery Link
                  </button>
                </form>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
