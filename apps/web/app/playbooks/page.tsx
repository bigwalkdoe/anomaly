"use client";

import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { Button } from "@/components/ui/button";
import { List, Plus } from "@/components/ui/icons";

export default function PlaybooksPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Automation
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">Playbooks</h1>
              <p className="text-sm text-muted-foreground">
                Create and execute multi-step tool workflows.
              </p>
            </div>
            <Button asChild>
              <Link href="/playbooks/new">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New playbook
              </Link>
            </Button>
          </div>

          <div className="rounded-xl border border-border bg-card p-8">
            <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 py-12 text-center">
              <List className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
              <div>
                <h3 className="text-sm font-semibold text-foreground">No playbooks</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Create a playbook to automate repeatable tool execution.
                </p>
              </div>
              <Button asChild size="sm" className="mt-2">
                <Link href="/playbooks/new">Create playbook</Link>
              </Button>
            </div>
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
