import {
  Activity,
  BarChart3,
  Bot,
  Database,
  LayoutDashboard,
  PieChart,
  ShieldCheck,
  Sparkles,
  UserCircle,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItemConfig {
  path: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  badgeVariant?: "new" | "count" | "default";
}

export interface NavGroupConfig {
  group: string;
  items: NavItemConfig[];
}

export const navGroups: NavGroupConfig[] = [
  {
    group: "WORKSPACE",
    items: [
      { path: "/", label: "Executive Overview", icon: LayoutDashboard },
      { path: "/customers", label: "Customer Intelligence", icon: Users },
      { path: "/segments", label: "Segmentation", icon: PieChart },
      { path: "/recommendations", label: "Recommendations", icon: Sparkles, badge: "Hybrid" },
      { path: "/analytics", label: "Business Analytics", icon: BarChart3 },
    ],
  },
  {
    group: "AI WORKSPACE",
    items: [
      { path: "/copilot", label: "Insights Copilot", icon: Bot, badge: "AI", badgeVariant: "new" },
      { path: "/audit", label: "Audit History", icon: ShieldCheck },
    ],
  },
  {
    group: "PLATFORM",
    items: [
      { path: "/monitoring", label: "Model Monitoring", icon: Activity, badge: "Live" },
      { path: "/data", label: "Data & Pipeline", icon: Database },
      { path: "/profile", label: "Profile & Settings", icon: UserCircle },
    ],
  },
];
