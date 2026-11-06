"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, ShieldCheck, Layout, Target, Activity, BarChart2, FileText } from "lucide-react";

/** Legacy navbar retained for compatibility; primary shell is `components/layout/layout`. */
export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="border-b border-border bg-background text-foreground">
      <div className="flex flex-1 items-center justify-between px-4 py-3">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
        >
          <ShieldCheck className="h-5 w-5 text-primary" />
          <span>Anomaly</span>
        </Link>

        <div className="hidden items-center gap-2 text-sm font-medium md:flex">
          <NavLink href="/" icon={<Layout className="h-4 w-4" />}>Dashboard</NavLink>
          <NavLink href="/engagements" icon={<Target className="h-4 w-4" />}>Engagements</NavLink>
          <NavLink href="/findings" icon={<Activity className="h-4 w-4" />}>Findings</NavLink>
          <NavLink href="/runs" icon={<BarChart2 className="h-4 w-4" />}>Runs</NavLink>
          <NavLink href="/reports" icon={<FileText className="h-4 w-4" />}>Reports</NavLink>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Sign in
          </Link>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-md p-1.5 text-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="space-y-1 border-t border-border bg-background px-4 py-4 md:hidden">
          <NavLink href="/" icon={<Layout className="h-4 w-4" />}>Dashboard</NavLink>
          <NavLink href="/engagements" icon={<Target className="h-4 w-4" />}>Engagements</NavLink>
          <NavLink href="/findings" icon={<Activity className="h-4 w-4" />}>Findings</NavLink>
          <NavLink href="/runs" icon={<BarChart2 className="h-4 w-4" />}>Runs</NavLink>
          <NavLink href="/reports" icon={<FileText className="h-4 w-4" />}>Reports</NavLink>
          <Link
            href="/login"
            className="block w-full rounded-md px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {icon}
      {children}
    </Link>
  );
}
