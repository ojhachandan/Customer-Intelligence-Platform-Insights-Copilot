import { lazy, Suspense } from "react";
import { Route, Routes, useLocation, Navigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { ThemeProvider } from "../context/ThemeContext";
import { AuthProvider } from "../context/AuthContext";
import { SidebarProvider } from "../context/SidebarContext";
import { ProtectedRoute } from "../components/auth/ProtectedRoute";
import { AppShell } from "../components/layout/AppShell";
import { PageTransition } from "../components/ui/page-transition";

const AuthPage = lazy(() => import("../pages/AuthPage"));
const DashboardPage = lazy(() => import("../pages/DashboardPage"));
const CustomerPage = lazy(() => import("../pages/CustomerPage"));
const SegmentsPage = lazy(() => import("../pages/SegmentsPage"));
const RecommendationsPage = lazy(() => import("../pages/RecommendationsPage"));
const AnalyticsPage = lazy(() => import("../pages/AnalyticsPage"));
const CopilotPage = lazy(() => import("../pages/CopilotPage"));
const AuditPage = lazy(() => import("../pages/AuditPage"));
const MonitoringPage = lazy(() => import("../pages/MonitoringPage"));
const DataPage = lazy(() => import("../pages/DataPage"));
const ProfilePage = lazy(() => import("../pages/ProfilePage"));

function PageFallback() {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-7 w-7 animate-spin rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)]" />
    </div>
  );
}

export function App() {
  const location = useLocation();

  return (
    <ThemeProvider>
      <AuthProvider>
        <SidebarProvider>
          <Suspense fallback={<PageFallback />}>
            <AnimatePresence mode="wait">
              <Routes location={location} key={location.pathname}>
                {/* Public Authentication Routes */}
                <Route path="/auth" element={<AuthPage />} />
                <Route path="/login" element={<AuthPage />} />
                <Route path="/signup" element={<AuthPage />} />

                {/* Protected Application Routes inside AppShell */}
                <Route
                  path="/*"
                  element={
                    <ProtectedRoute>
                      <AppShell>
                        <Suspense fallback={<PageFallback />}>
                          <AnimatePresence mode="wait">
                            <Routes location={location} key={location.pathname}>
                              <Route
                                path="/"
                                element={
                                  <PageTransition>
                                    <DashboardPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/customers"
                                element={
                                  <PageTransition>
                                    <CustomerPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/segments"
                                element={
                                  <PageTransition>
                                    <SegmentsPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/recommendations"
                                element={
                                  <PageTransition>
                                    <RecommendationsPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/analytics"
                                element={
                                  <PageTransition>
                                    <AnalyticsPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/copilot"
                                element={
                                  <PageTransition>
                                    <CopilotPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/audit"
                                element={
                                  <PageTransition>
                                    <AuditPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/monitoring"
                                element={
                                  <PageTransition>
                                    <MonitoringPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/data"
                                element={
                                  <PageTransition>
                                    <DataPage />
                                  </PageTransition>
                                }
                              />
                              <Route
                                path="/profile"
                                element={
                                  <PageTransition>
                                    <ProfilePage />
                                  </PageTransition>
                                }
                              />
                              {/* Catch-all fallback */}
                              <Route path="*" element={<Navigate to="/" replace />} />
                            </Routes>
                          </AnimatePresence>
                        </Suspense>
                      </AppShell>
                    </ProtectedRoute>
                  }
                />
              </Routes>
            </AnimatePresence>
          </Suspense>
        </SidebarProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}