"use client";

import * as React from "react";
import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  Target,
  Activity,
  FileText,
  Play,
  Settings,
  Shield,
  Users,
  List,
  Clock,
  BarChart3,
  LogOut,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Engagements", href: "/engagements", icon: Target },
  { name: "Findings", href: "/findings", icon: Activity },
  { name: "Runs", href: "/runs", icon: Play },
  { name: "Reports", href: "/reports", icon: FileText },
  { name: "Playbooks", href: "/playbooks", icon: List },
  { name: "Schedules", href: "/schedules", icon: Clock },
  { name: "Settings", href: "/settings", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-50 h-screen border-r border-input bg-background transition-transform duration-300",
        collapsed ? "-translate-x-full w-64" : "translate-x-0 w-64"
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between h-12 px-4">
          <Link href="/" className="flex items-center gap-2 px-3 py-1 font-semibold tracking-tight">
            <Shield className="h-6 w-6 text-primary" />
            <span className={cn("hidden", !collapsed && "block")}>Anomaly</span>
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-muted-foreground hover:text-primary"
            aria-label="Toggle sidebar"
          >
            <ChevronRight className={cn("h-5 w-5 transition-transform duration-300", collapsed && "rotate-180")} />
          </button>
        </div>
        <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className={cn("h-5 w-5 shrink-0", isActive && "text-primary")} />
                <span className={cn("hidden", !collapsed && "block")}>{item.name}</span>
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-input p-3">
          <Link
            href="/login"
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <LogOut className="h-5 w-5 shrink-0" />
            <span className={cn("hidden", !collapsed && "block")}>Sign out</span>
          </Link>
        </div>
      </div>
    </aside>
  );
}

export function TopNav({ user }: { user?: { name?: string; email?: string } }) {
  return (
    <div className="sticky top-0 z-40 flex h-12 items-center justify-between px-4 border-b border-input bg-background">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 font-semibold tracking-tight">
          <Shield className="h-6 w-6 text-primary" />
          <span className="hidden md:block">Anomaly</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button className="hidden md:flex items-center gap-2 rounded-md px-3 py-1 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
          <Users className="h-4 w-4" />
          <span>{user?.name || "Admin"}</span>
          <svg
            className="ml-1 h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="m19 9-2 2l-2-2" />
          </svg>
        </button>
        <Link href="/login" className="hidden md:flex items-center gap-2 rounded-md px-3 py-1 text-sm font-medium text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors">
          <LogOut className="h-4 w-4" />
          Sign out
        </Link>
        <button className="p-1 text-muted-foreground hover:text-primary">
          <svg
            className="h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
