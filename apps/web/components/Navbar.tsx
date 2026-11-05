"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X, ShieldCheck, Layout, Target, Activity, BarChart2, FileText, LogOut } from "lucide-react";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="border-b border-border bg-white">
      <div className="flex flex-1 items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <ShieldCheck className="h-5 w-5 text-primary" />
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
          <Link href="/login" className="text-sm text-destructive hover:bg-red-50 rounded-md px-3 py-1.5 transition-colors">
            Sign in
          </Link>
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
        <div className="md:hidden border-t border-border bg-white px-4 py-4 space-y-2">
          <NavLink href="/" icon={<Layout className="h-4 w-4" />}>Dashboard</NavLink>
          <NavLink href="/engagements" icon={<Target className="h-4 w-4" />}>Engagements</NavLink>
          <NavLink href="/findings" icon={<Activity className="h-4 w-4" />}>Findings</NavLink>
          <NavLink href="/runs" icon={<BarChart2 className="h-4 w-4" />}>Runs</NavLink>
          <NavLink href="/reports" icon={<FileText className="h-4 w-4" />}>Reports</NavLink>
          <Link
            href="/login"
            className="w-full text-left text-sm text-destructive hover:bg-red-50 rounded-md px-3 py-2 transition-colors"
          >
            Sign in
          </Link>
        </div>
      )}
    </nav>
  );
}

function NavLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-primary transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
