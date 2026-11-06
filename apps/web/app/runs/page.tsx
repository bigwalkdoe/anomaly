"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { statusVariant } from "@/components/ui/status";
import { ArrowRight, Plus, Play } from "@/components/ui/icons";

interface Run {
  id: string;
  engagement_id: string;
  tool: string;
  status: string;
  scope_warning: boolean;
}

function RunStatusBadge({ value }: { value: string }) {
  const variant = statusVariant("run", value);
  return (
    <Badge variant="outline" className={variant.className}>
      {variant.label}
    </Badge>
  );
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiJson<Run[]>("/api/runs?limit=100")
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Execution
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
              <p className="text-sm text-muted-foreground">
                Monitor tool execution status and scope signals.
              </p>
            </div>
            <Button asChild>
              <Link href="/engagements/new">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New run
              </Link>
            </Button>
          </div>

          <div className="rounded-xl border border-border bg-card">
            {loading ? (
              <div className="flex h-64 items-center justify-center">
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  Loading runs…
                </div>
              </div>
            ) : runs.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run</TableHead>
                    <TableHead>Tool</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {run.id.slice(0, 8)}…
                      </TableCell>
                      <TableCell className="font-medium">{run.tool}</TableCell>
                      <TableCell>
                        <RunStatusBadge value={run.status} />
                      </TableCell>
                      <TableCell>
                        {run.scope_warning ? (
                          <Badge
                            variant="outline"
                            className="bg-status-warning text-status-warning-foreground border-status-warning-border"
                          >
                            Scope warning
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">No warning</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button asChild variant="ghost" size="icon" className="h-8 w-8">
                          <Link href={`/runs/${run.id}`} aria-label={`View run ${run.id}`}>
                            <ArrowRight className="h-4 w-4" aria-hidden="true" />
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="p-8">
                <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 py-12 text-center">
                  <Play className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">No runs</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Start a tool run from an engagement to see results here.
                    </p>
                  </div>
                  <Button asChild size="sm" className="mt-2">
                    <Link href="/engagements/new">Create engagement</Link>
                  </Button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
