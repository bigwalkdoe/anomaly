"use client";

import Link from "next/link";
import { useAuth } from "@/components/AuthContext";
import { useState } from "react";
import { LogOut, Menu, X, ShieldCheck, Target, Activity, Layout, BarChart2, FileText } from "lucide-react";

export function Navbar() {
  const { token, logout, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!isAuthenticated) {
    return (
      <nav className="border-b border-border bg-background">
        <div className="flex flex-1 items-center justify-between px-4 py-3">
          <Link href="/login" className="font-semibold tracking-tight">
            Anomaly
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium rounded-md bg-primary px-3 py-1.5 text-primary-foreground hover:bg-primary/90">
              Sign in
            </Link>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="border-b border-border bg-background">
      <div className="flex flex-1 items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <ShieldCheck className="h-5 w-5" />
          <span>Anomaly</span>
        </Link>

        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          <NavLink href="/" icon={<Layout className="h-4 w-4" />}>Dashboard</NavLink>
          <NavLink href="/engagements" icon={<Target className="h-4 w-4" />}>Engagements</NavLink>
          <NavLink href="/findings" icon={<Activity className="h-4 w-4" />}>Findings</NavLink>
          <NavLink href="/runs" icon={<BarChart2 className="h-4 w-4" />}>Runs</NavLink>
          <NavLink href="/reports" icon={<FileText className="h-4 w-4" />}>Reports</NavLink>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => logout()}
            className="text-sm text-destructive hover:bg-destructive/10 rounded-md px-3 py-1.5 transition-colors"
          >
            Sign out
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-foreground"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-background px-4 py-4 space-y-2">
          <MobileNavLink href="/" icon={<Layout className="h-4 w-4" />}>Dashboard</MobileNavLink>
          <MobileNavLink href="/engagements" icon={<Target className="h-4 w-4" />}>Engagements</MobileNavLink>
          <MobileNavLink href="/findings" icon={<Activity className="h-4 w-4" />}>Findings</MobileNavLink>
          <MobileNavLink href="/runs" icon={<BarChart2 className="h-4 w-4" />}>Runs</MobileNavLink>
          <MobileNavLink href="/reports" icon={<FileText className="h-4 w-4" />}>Reports</MobileNavLink>
          <button
            onClick={() => logout()}
            className="w-full text-left text-sm text-destructive hover:bg-destructive/10 rounded-md px-3 py-2 transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </nav>
  );
}

function NavLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: string }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        isOpen ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
      }`}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      {icon}
      {children}
    </Link>
  );
}

function MobileNavLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
