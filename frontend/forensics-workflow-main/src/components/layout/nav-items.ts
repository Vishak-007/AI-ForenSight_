import {
  FileUp,
  FileText,
  LayoutDashboard,
  ListTree,
  Users,
  ShieldAlert,
  Images,
  Settings as SettingsIcon,
} from "lucide-react";

export interface NavItem {
  to: "/upload" | "/report" | "/dashboard" | "/timeline" | "/entities" | "/flags" | "/media" | "/settings";
  label: string;
  icon: typeof LayoutDashboard;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    to: "/upload",
    label: "New Investigation",
    icon: FileUp,
    description: "Upload a UFDR file and run forensic analysis",
  },
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    description: "Case overview and evidence statistics",
  },
  {
    to: "/timeline",
    label: "Timeline",
    icon: ListTree,
    description: "Chronological evidence investigation",
  },
  { to: "/entities", label: "Entities", icon: Users, description: "People, phones and locations" },
  { to: "/flags", label: "Flags", icon: ShieldAlert, description: "AI-derived analysis flags" },
  { to: "/media", label: "Media", icon: Images, description: "Images and audio evidence" },
  {
    to: "/report",
    label: "Final Report",
    icon: FileText,
    description: "Investigation report preview and PDF export",
  },
  {
    to: "/settings",
    label: "Settings",
    icon: SettingsIcon,
    description: "Account and application preferences",
  },
];
