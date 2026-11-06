"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/AuthContext";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  Activity,
  ChevronRight,
  Clock,
  FileText,
  Layout,
  List,
  LogOut,
  Menu,
  Play,
  Settings,
  Shield,
  Target,
  X,
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

type ShellState = { mobileOpen: boolean };
let shellState: ShellState = { mobileOpen: false };
const shellListeners = new Set<() => void>();

function emitShell() {
  shellListeners.forEach((l) => l());
}

function setMobileOpen(mobileOpen: boolean) {
  if (shellState.mobileOpen === mobileOpen) return;
  shellState = { mobileOpen };
  emitShell();
}

function subscribeShell(listener: () => void) {
  shellListeners.add(listener);
  return () => shellListeners.delete(listener);
}

function getShellSnapshot() {
  return shellState;
}

function useShell() {
  const state = React.useSyncExternalStore(
    subscribeShell,
    getShellSnapshot,
    getShellSnapshot
  );
  return {
    mobileOpen: state.mobileOpen,
    openMobile: () => setMobileOpen(true),
    closeMobile: () => setMobileOpen(false),
  };
}

function isNavActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Primary">
      {navigation.map((item) => {
        const isActive = isNavActive(pathname, item.href);
        return (
          <Link
            key={item.name}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            )}
          >
            <item.icon
              className={cn(
                "h-4 w-4 shrink-0",
                isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
              )}
              aria-hidden="true"
            />
            <span>{item.name}</span>
            {isActive ? (
              <ChevronRight className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}

function Brand() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2.5 rounded-md px-2 py-1 font-semibold tracking-tight text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-card text-primary">
        <Shield className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="flex flex-col leading-none">
        <span className="text-sm">Anomaly</span>
        <span className="text-[11px] font-normal text-muted-foreground">Operations</span>
      </span>
    </Link>
  );
}

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { logout } = useAuth();
  const { mobileOpen, closeMobile } = useShell();

  React.useEffect(() => {
    closeMobile();
  }, [pathname, closeMobile]);

  const handleSignOut = () => {
    closeMobile();
    logout();
    router.replace("/login");
  };

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-40 bg-background/80 backdrop-blur-sm transition-opacity md:hidden",
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        aria-hidden="true"
        onClick={closeMobile}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card text-card-foreground transition-transform duration-200 ease-out",
          "md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-14 items-center justify-between border-b border-border px-3">
          <Brand />
          <button
            type="button"
            onClick={closeMobile}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <NavLinks onNavigate={closeMobile} />
        <div className="border-t border-border p-3">
          <div className="mb-2 flex items-center justify-between px-1">
            <span className="text-xs font-medium text-muted-foreground">Theme</span>
            <ThemeToggle />
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
}

export function TopNav({ user }: { user?: { name?: string; email?: string } }) {
  const router = useRouter();
  const { logout } = useAuth();
  const { mobileOpen, openMobile } = useShell();

  const handleSignOut = () => {
    logout();
    router.replace("/login");
  };

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:pl-[17rem] md:pr-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={openMobile}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
          aria-label={mobileOpen ? "Navigation open" : "Open navigation"}
          aria-expanded={mobileOpen}
        >
          <Menu className="h-4 w-4" aria-hidden="true" />
        </button>
        <div className="hidden min-w-0 md:block">
          <p className="truncate text-sm font-medium text-foreground">Security Operations</p>
          <p className="truncate text-xs text-muted-foreground">Engagements, findings, and runs</p>
        </div>
        <div className="flex items-center gap-2 md:hidden">
          <Shield className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold">Anomaly</span>
        </div>
      </div>
      <div className="flex items-center gap-1 sm:gap-2">
        {user?.name || user?.email ? (
          <span className="hidden max-w-[180px] truncate text-sm text-muted-foreground lg:inline">
            {user.name || user.email}
          </span>
        ) : null}
        <ThemeToggle />
        <button
          type="button"
          onClick={handleSignOut}
          className="hidden items-center gap-2 rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:inline-flex"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          <span>Sign out</span>
        </button>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav />
      <Sidebar />
      <main className="md:ml-64">{children}</main>
    </div>
  );
}
