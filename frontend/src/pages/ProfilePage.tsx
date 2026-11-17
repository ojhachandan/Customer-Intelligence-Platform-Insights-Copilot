import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Camera,
  Check,
  CheckCircle2,
  Globe,
  Laptop,
  Mail,
  Moon,
  Palette,
  Shield,
  Smartphone,
  Sun,
  User,
  UserCircle,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { PageHeader } from "../components/ui/page-header";
import { PasswordStrengthMeter } from "../components/auth/PasswordStrengthMeter";

function calculateCompleteness(user: ReturnType<typeof useAuth>["user"]): {
  percent: number;
  missing: string[];
} {
  if (!user) return { percent: 0, missing: [] };
  const fields = [
    { name: "Full Name", val: user.name },
    { name: "Avatar Image", val: user.avatar },
    { name: "Phone Number", val: user.phone },
    { name: "Job Title", val: user.jobTitle },
    { name: "Company", val: user.company },
    { name: "Location", val: user.location },
    { name: "Bio Summary", val: user.bio },
  ];
  const filled = fields.filter((f) => !!f.val && f.val.trim().length > 0);
  const missing = fields.filter((f) => !f.val || f.val.trim().length === 0).map((f) => f.name);
  const percent = Math.round((filled.length / fields.length) * 100);
  return { percent, missing };
}

export default function ProfilePage() {
  const { user, updateProfile, changePassword, deleteAccount } = useAuth();
  const { theme, setTheme } = useTheme();

  const [activeTab, setActiveTab] = useState<"profile" | "account" | "security" | "preferences" | "danger">("profile");
  const [isEditing, setIsEditing] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Profile Edit State
  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [jobTitle, setJobTitle] = useState(user?.jobTitle || "");
  const [company, setCompany] = useState(user?.company || "");
  const [location, setLocation] = useState(user?.location || "");
  const [bio, setBio] = useState(user?.bio || "");
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar || "");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Security State
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [securityError, setSecurityError] = useState<string | null>(null);

  // Preferences State
  const [emailAlerts, setEmailAlerts] = useState(user?.preferences?.emailAlerts ?? true);
  const [weeklyDigest, setWeeklyDigest] = useState(user?.preferences?.weeklyDigest ?? true);
  const [reducedMotion, setReducedMotion] = useState(user?.preferences?.reducedMotion ?? false);
  const [density, setDensity] = useState<"comfortable" | "compact">(user?.preferences?.density ?? "comfortable");

  // Danger Modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteConfirmEmail, setDeleteConfirmEmail] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      alert("File size exceeds 2MB limit.");
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      setAvatarPreview(base64);
      void updateProfile({ avatar: base64 });
      showToast("Profile avatar updated");
    };
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateProfile({
      name,
      phone,
      jobTitle,
      company,
      location,
      bio,
      avatar: avatarPreview,
    });
    setIsEditing(false);
    showToast("Profile changes saved successfully");
  };

  const handleSavePreferences = async () => {
    await updateProfile({
      preferences: {
        theme,
        emailAlerts,
        weeklyDigest,
        reducedMotion,
        density,
      },
    });
    showToast("Preferences saved");
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSecurityError(null);
    if (newPassword !== confirmPassword) {
      setSecurityError("New passwords do not match.");
      return;
    }
    try {
      await changePassword(oldPassword, newPassword);
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      showToast("Password updated successfully");
    } catch (err) {
      setSecurityError(err instanceof Error ? err.message : "Failed to update password");
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeleteError(null);
    try {
      await deleteAccount(deleteConfirmEmail);
      setDeleteModalOpen(false);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete account");
    }
  };

  const completeness = calculateCompleteness(user);

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "account", label: "Account", icon: Globe },
    { id: "security", label: "Security & Sessions", icon: Shield },
    { id: "preferences", label: "Preferences", icon: Palette },
    { id: "danger", label: "Danger Zone", icon: AlertTriangle },
  ] as const;

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Settings & Profile"
        subtitle="Manage your identity, credentials, application theme, and session security."
        icon={UserCircle}
      />

      {/* Floating Success Toast */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-[14px] border border-[#84CC16]/30 bg-[var(--bg-surface)] px-4 py-3 text-xs font-medium text-[var(--text-primary)] shadow-elevated"
          >
            <CheckCircle2 size={16} className="text-[#84CC16]" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Top Profile Summary & Progress Ring Card */}
      <div className="card p-6 flex flex-col sm:flex-row items-center gap-6 justify-between shadow-card">
        <div className="flex items-center gap-4">
          <div className="relative group">
            {user?.avatar || avatarPreview ? (
              <img
                src={avatarPreview || user?.avatar}
                alt={user?.name}
                className="h-16 w-16 rounded-full object-cover border-2 border-[var(--border-subtle)]"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--accent-soft)] font-serif text-2xl font-bold text-[var(--accent)] border-2 border-[var(--accent-border)]">
                {user?.firstName?.charAt(0)}
                {user?.lastName?.charAt(0)}
              </div>
            )}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--on-accent)] shadow-soft transition-transform hover:scale-110"
              aria-label="Upload avatar image"
            >
              <Camera size={12} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarChange}
            />
          </div>

          <div>
            <h2 className="heading-serif text-xl font-bold text-[var(--text-primary)]">{user?.name}</h2>
            <p className="text-xs text-[var(--text-muted)] flex items-center gap-2 mt-0.5">
              <span>{user?.jobTitle}</span>
              <span>·</span>
              <span>{user?.company}</span>
            </p>
            <div className="flex items-center gap-2 mt-2 text-[11px] text-[var(--text-muted)]">
              <Mail size={12} /> <span>{user?.email}</span>
            </div>
          </div>
        </div>

        {/* Profile Completeness Ring */}
        <div className="flex items-center gap-4 border-t sm:border-t-0 sm:border-l border-[var(--border-subtle)] pt-4 sm:pt-0 sm:pl-6">
          <div className="relative flex h-14 w-14 items-center justify-center">
            <svg className="h-14 w-14 -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-[var(--bg-subtle)]"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className="text-[var(--accent)]"
                strokeDasharray={`${completeness.percent}, 100`}
                strokeWidth="3.5"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <span className="absolute font-mono text-xs font-bold text-[var(--text-primary)]">
              {completeness.percent}%
            </span>
          </div>
          <div>
            <p className="text-xs font-semibold text-[var(--text-primary)]">Profile Completeness</p>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              {completeness.missing.length === 0
                ? "All recommended fields completed!"
                : `Add ${completeness.missing[0]} to reach 100%`}
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-[var(--border-subtle)]">
        <nav className="flex gap-2 sm:gap-4 overflow-x-auto pb-px" aria-label="Profile tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setIsEditing(false);
                }}
                className={`relative flex items-center gap-2 whitespace-nowrap px-3.5 pb-3 text-xs font-medium transition-colors ${
                  isActive ? "text-[var(--accent)]" : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="profileTabUnderline"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--accent)] rounded-full"
                  />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* TAB 1: PROFILE */}
      {activeTab === "profile" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="card p-6 shadow-card">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-4 mb-5">
              <div>
                <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">
                  Personal Information
                </h3>
                <p className="text-xs text-[var(--text-muted)]">
                  Your biographical details and enterprise role information.
                </p>
              </div>
              {!isEditing && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="btn-secondary text-xs"
                >
                  Edit Profile
                </button>
              )}
            </div>

            {isEditing ? (
              <form onSubmit={handleSaveProfile} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="label block mb-1">Full Name</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="label block mb-1">Phone Number</label>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1 (555) 000-0000"
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="label block mb-1">Job Title</label>
                    <input
                      type="text"
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="label block mb-1">Organization / Company</label>
                    <input
                      type="text"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="label block mb-1">Location</label>
                    <input
                      type="text"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      placeholder="City, Country"
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="label block mb-1">Timezone</label>
                    <input
                      type="text"
                      readOnly
                      value={user?.timezone}
                      className="input w-full opacity-70 bg-[var(--bg-subtle)] cursor-not-allowed"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="label">Bio Summary</label>
                    <span className="text-[10px] text-[var(--text-muted)]">{bio.length} / 250 characters</span>
                  </div>
                  <textarea
                    rows={3}
                    maxLength={250}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    className="input w-full resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-subtle)]">
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="btn-ghost text-xs"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary text-xs py-2 px-4">
                    Save Changes
                  </button>
                </div>
              </form>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 text-xs">
                <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Full Name</span>
                  <p className="mt-1 font-semibold text-sm text-[var(--text-primary)]">{user?.name}</p>
                </div>
                <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Phone Number</span>
                  <p className="mt-1 text-sm text-[var(--text-primary)]">{user?.phone || "—"}</p>
                </div>
                <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Job Title</span>
                  <p className="mt-1 text-sm text-[var(--text-primary)]">{user?.jobTitle || "—"}</p>
                </div>
                <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Company</span>
                  <p className="mt-1 text-sm text-[var(--text-primary)]">{user?.company || "—"}</p>
                </div>
                <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Location</span>
                  <p className="mt-1 text-sm text-[var(--text-primary)]">{user?.location || "—"}</p>
                </div>
                <div className="rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Timezone</span>
                  <p className="mt-1 text-sm text-[var(--text-primary)]">{user?.timezone || "—"}</p>
                </div>
                <div className="sm:col-span-2 rounded-[14px] bg-[var(--bg-subtle)] p-3.5">
                  <span className="label block text-[10px]">Bio Summary</span>
                  <p className="mt-1 text-sm text-[var(--text-secondary)] leading-relaxed">{user?.bio || "No biography provided."}</p>
                </div>
                <div className="rounded-[14px] border border-[var(--border-subtle)] p-3 text-[11px] text-[var(--text-muted)]">
                  <span>Member Since: </span>
                  <strong className="text-[var(--text-primary)]">{user?.memberSince}</strong>
                </div>
                <div className="rounded-[14px] border border-[var(--border-subtle)] p-3 text-[11px] text-[var(--text-muted)]">
                  <span>Last Workspace Activity: </span>
                  <strong className="text-[var(--text-primary)]">{user?.lastLogin}</strong>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* TAB 2: ACCOUNT */}
      {activeTab === "account" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="card p-6 shadow-card space-y-5">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Account Credentials</h3>
              <p className="text-xs text-[var(--text-muted)]">Manage primary email contact and domain access.</p>
            </div>
            <div className="flex items-center justify-between rounded-[14px] bg-[var(--bg-subtle)] p-4">
              <div>
                <p className="text-xs font-semibold text-[var(--text-primary)]">{user?.email}</p>
                <p className="text-[11px] text-[#84CC16] flex items-center gap-1 mt-0.5">
                  <Check size={12} /> Primary verified work email
                </p>
              </div>
              <button
                type="button"
                onClick={() => showToast("Email change verification link dispatched")}
                className="btn-secondary text-xs"
              >
                Change Email
              </button>
            </div>
          </div>

          <div className="card p-6 shadow-card space-y-4">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Connected Identity Providers</h3>
              <p className="text-xs text-[var(--text-muted)]">Single sign-on integrations for enterprise access.</p>
            </div>
            <div className="divide-y divide-[var(--border-subtle)]">
              <div className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--bg-subtle)] text-[var(--text-primary)]">
                    <Globe size={16} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[var(--text-primary)]">Google Workspace SSO</p>
                    <p className="text-[11px] text-[var(--text-muted)]">Enterprise domain federated identity</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => showToast("Google SSO integration toggled")}
                  className="btn-secondary text-xs"
                >
                  Connect
                </button>
              </div>

              <div className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-[var(--bg-subtle)] text-[var(--text-primary)]">
                    <Laptop size={16} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-[var(--text-primary)]">GitHub Enterprise</p>
                    <p className="text-[11px] text-[var(--text-muted)]">Developer instance authentication</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => showToast("GitHub integration toggled")}
                  className="btn-secondary text-xs"
                >
                  Connect
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* TAB 3: SECURITY & SESSIONS */}
      {activeTab === "security" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="card p-6 shadow-card space-y-4">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Update Password</h3>
              <p className="text-xs text-[var(--text-muted)]">Ensure your account is protected with a resilient passkey.</p>
            </div>

            {securityError && (
              <div className="rounded-[12px] border border-[#C4554D]/30 bg-[#C4554D]/10 p-3 text-xs text-[#C4554D]">
                {securityError}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
              <div>
                <label className="label block mb-1">Current Password</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="input w-full"
                />
              </div>
              <div>
                <label className="label block mb-1">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input w-full"
                />
                <PasswordStrengthMeter password={newPassword} />
              </div>
              <div>
                <label className="label block mb-1">Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input w-full"
                />
              </div>
              <button type="submit" className="btn-primary text-xs py-2 px-4">
                Update Password
              </button>
            </form>
          </div>

          <div className="card p-6 shadow-card space-y-4">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Active Sessions</h3>
              <p className="text-xs text-[var(--text-muted)]">Authorized browser devices currently connected to your account.</p>
            </div>
            <div className="space-y-3">
              {user?.sessions?.map((sess) => (
                <div
                  key={sess.id}
                  className="flex items-center justify-between rounded-[14px] bg-[var(--bg-subtle)] p-3.5 border border-[var(--border-subtle)]"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-[var(--bg-surface)] text-[var(--text-primary)]">
                      {sess.device.includes("iPhone") ? <Smartphone size={16} /> : <Laptop size={16} />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-semibold text-[var(--text-primary)]">{sess.device}</p>
                        {sess.isCurrent && (
                          <span className="rounded-full bg-[#84CC16]/15 px-2 py-0.2 text-[9px] font-bold text-[#84CC16]">
                            Current Session
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                        {sess.location} · {sess.lastActive}
                      </p>
                    </div>
                  </div>
                  {!sess.isCurrent && (
                    <button
                      type="button"
                      onClick={() => showToast("Device session terminated")}
                      className="btn-secondary text-[11px] py-1.5 px-3 text-[#C4554D] hover:bg-[#C4554D]/10"
                    >
                      Revoke Access
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* TAB 4: PREFERENCES */}
      {activeTab === "preferences" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="card p-6 shadow-card space-y-5">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Interface Theme</h3>
              <p className="text-xs text-[var(--text-muted)]">Choose how the Customer Intelligence Platform appears to you.</p>
            </div>

            <div className="grid grid-cols-3 gap-3 max-w-md">
              {(["light", "dark", "system"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => {
                    setTheme(t);
                    showToast(`Theme changed to ${t}`);
                  }}
                  className={`flex flex-col items-center gap-2 rounded-[14px] p-3.5 border text-xs font-semibold capitalize transition-all ${
                    theme === t
                      ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)] shadow-soft"
                      : "border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-hover)]"
                  }`}
                >
                  {t === "light" && <Sun size={18} />}
                  {t === "dark" && <Moon size={18} />}
                  {t === "system" && <Palette size={18} />}
                  <span>{t}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="card p-6 shadow-card space-y-4">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[var(--text-primary)]">Notification Preferences</h3>
              <p className="text-xs text-[var(--text-muted)]">Configure frequency and delivery channels for model alerts.</p>
            </div>

            <div className="divide-y divide-[var(--border-subtle)]">
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Real-time Feature Drift Alerts</p>
                  <p className="text-[11px] text-[var(--text-muted)]">Receive alerts when population stability index (PSI) breaches 0.25</p>
                </div>
                <input
                  type="checkbox"
                  checked={emailAlerts}
                  onChange={(e) => setEmailAlerts(e.target.checked)}
                  style={{ accentColor: "var(--accent)" }}
                  className="h-4 w-4 rounded border-[var(--border-subtle)] text-[var(--accent)] accent-[var(--accent)] focus:ring-[var(--accent)]"
                />
              </div>

              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Weekly Executive Digest</p>
                  <p className="text-[11px] text-[var(--text-muted)]">Summarized revenue trajectories and cluster migration report</p>
                </div>
                <input
                  type="checkbox"
                  checked={weeklyDigest}
                  onChange={(e) => setWeeklyDigest(e.target.checked)}
                  style={{ accentColor: "var(--accent)" }}
                  className="h-4 w-4 rounded border-[var(--border-subtle)] text-[var(--accent)] accent-[var(--accent)] focus:ring-[var(--accent)]"
                />
              </div>

              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Reduce Motion</p>
                  <p className="text-[11px] text-[var(--text-muted)]">Minimize UI animations and floating parallax effects</p>
                </div>
                <input
                  type="checkbox"
                  checked={reducedMotion}
                  onChange={(e) => setReducedMotion(e.target.checked)}
                  style={{ accentColor: "var(--accent)" }}
                  className="h-4 w-4 rounded border-[var(--border-subtle)] text-[var(--accent)] accent-[var(--accent)] focus:ring-[var(--accent)]"
                />
              </div>
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)]">Layout Density</p>
                  <p className="text-[11px] text-[var(--text-muted)]">Control spacing in data tables and analytics cards</p>
                </div>
                <div className="flex rounded-[10px] bg-[var(--bg-subtle)] p-0.5 border border-[var(--border-subtle)]">
                  <button
                    type="button"
                    onClick={() => setDensity("comfortable")}
                    className={`px-2.5 py-1 text-[11px] rounded-[8px] font-medium transition-colors ${
                      density === "comfortable"
                        ? "bg-[var(--accent)] text-[var(--on-accent)]"
                        : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    }`}
                  >
                    Comfortable
                  </button>
                  <button
                    type="button"
                    onClick={() => setDensity("compact")}
                    className={`px-2.5 py-1 text-[11px] rounded-[8px] font-medium transition-colors ${
                      density === "compact"
                        ? "bg-[var(--accent)] text-[var(--on-accent)]"
                        : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                    }`}
                  >
                    Compact
                  </button>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSavePreferences}
              className="btn-primary text-xs py-2 px-4 mt-2"
            >
              Save Preferences
            </button>
          </div>
        </motion.div>
      )}

      {/* TAB 5: DANGER ZONE */}
      {activeTab === "danger" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="card p-6 border-[#C4554D]/30 bg-[#C4554D]/[0.03] shadow-card space-y-4">
            <div>
              <h3 className="heading-serif text-base font-semibold text-[#C4554D]">Danger Zone</h3>
              <p className="text-xs text-[var(--text-muted)]">
                Permanent actions affecting your access and persisted credentials.
              </p>
            </div>

            <div className="flex items-center justify-between rounded-[14px] bg-[var(--bg-surface)] p-4 border border-[#C4554D]/20">
              <div>
                <p className="text-xs font-semibold text-[var(--text-primary)]">Delete Account</p>
                <p className="text-[11px] text-[var(--text-muted)]">
                  Permanently erase your user profile and active workspace authorization.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDeleteModalOpen(true)}
                className="btn bg-[#C4554D] text-white hover:bg-[#B3453D] text-xs py-2 px-4"
              >
                Delete Account
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-xs"
              onClick={() => setDeleteModalOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="relative w-full max-w-sm rounded-[20px] border border-[#C4554D]/30 bg-[var(--bg-surface)] p-6 shadow-elevated"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="heading-serif text-lg font-bold text-[#C4554D]">Confirm Account Deletion</h3>
                <button
                  type="button"
                  onClick={() => setDeleteModalOpen(false)}
                  className="rounded-full p-1 text-[var(--text-muted)] hover:bg-[var(--bg-subtle)]"
                >
                  <X size={16} />
                </button>
              </div>

              {deleteError && (
                <div className="mb-4 rounded-[10px] bg-[#C4554D]/10 p-2.5 text-xs text-[#C4554D]">
                  {deleteError}
                </div>
              )}

              <form onSubmit={handleDeleteAccount} className="space-y-4">
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  This action is irreversible. Please type your email <strong className="text-[var(--text-primary)]">{user?.email}</strong> below to confirm.
                </p>
                <input
                  type="email"
                  required
                  value={deleteConfirmEmail}
                  onChange={(e) => setDeleteConfirmEmail(e.target.value)}
                  placeholder={user?.email}
                  className="input w-full text-xs"
                />
                <button
                  type="submit"
                  disabled={deleteConfirmEmail.toLowerCase() !== user?.email.toLowerCase()}
                  className="btn bg-[#C4554D] text-white hover:bg-[#B3453D] w-full text-xs py-2.5 disabled:opacity-50"
                >
                  Permanently Delete My Account
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
