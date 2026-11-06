"use client";

import * as React from "react";
import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/AuthContext";
import {
  Activity,
  ChevronRight,
  Clock,
  FileText,
  Layout,
  List,
  LogOut,
  Play,
  Settings,
  Shield,
  Target,
} from "@/components/ui/icons";

const navigation = [
  { name: "Dashboard", href: "/", icon: Layout },
  { name: "Engagements", href: "/engagements", icon: Target },
  { name: "Findings", href: "/findings", icon: Activity },
  { name: "Runs", href: "/runs", icon: Play },
  { name: "Reports", href: "/reports", icon: FileText },
  { name: "Playbooks", href: "/playbooks", icon: List },
  { name: "Schedules", href: "/schedules", icon: Clock },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const handleSignOut = () => {
    logout();
    router.replace("/login");
  };

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
            <span>Anomaly</span>
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-muted-foreground hover:text-primary"
            aria-label="Toggle sidebar"
            type="button"
          >
            <ChevronRight
              className={cn("h-5 w-5 transition-transform duration-300", collapsed && "rotate-180")}
            />
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
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-input p-3">
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <LogOut className="h-5 w-5 shrink-0" />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </aside>
  );
}

export function TopNav({ user }: { user?: { name?: string; email?: string } }) {
  const router = useRouter();
  const { logout } = useAuth();

  const handleSignOut = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="sticky top-0 z-40 flex h-12 items-center justify-between px-4 border-b border-input bg-background">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 font-semibold tracking-tight">
          <Shield className="h-6 w-6 text-primary" />
          <span className="hidden md:block">Anomaly</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {user?.name && (
          <span className="hidden md:inline text-sm text-muted-foreground">{user.name}</span>
        )}
        <button
          type="button"
          onClick={handleSignOut}
          className="hidden md:flex items-center gap-2 rounded-md px-3 py-1 text-sm font-medium text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
        <button className="p-1 text-muted-foreground hover:text-primary" aria-label="Activity" type="button">
          <Clock className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
