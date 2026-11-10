"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { statusVariant } from "@/components/ui/status";
import { ArrowLeft, Play } from "@/components/ui/icons";

interface Run {
  id: string;
  status: string;
  scope_warning: boolean;
}

export default function RunDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<Run>(`/api/runs/${id}`)
      .then(setRun)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load run"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <RequireAuth>
        <div className="min-h-screen bg-background text-foreground">
          <TopNav />
          <Sidebar />
          <main className="md:ml-64 p-4 pt-6 md:p-8 text-sm text-muted-foreground">Loading run…</main>
        </div>
      </RequireAuth>
    );
  }

  const st = run ? statusVariant("run", run.status) : null;

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-3">
            <Link
              href="/runs"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to runs
            </Link>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Execution</p>
              <h1 className="text-2xl font-semibold tracking-tight">Run detail</h1>
            </div>
          </div>

          {!run ? (
            <Card className="max-w-2xl">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-muted-foreground">
                  <Play className="h-4 w-4" aria-hidden="true" />
                </div>
                <CardTitle>Run unavailable</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">{error || "The requested run could not be loaded."}</p>
                <Button asChild variant="outline"><Link href="/runs">Back to runs</Link></Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="max-w-2xl">
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  {st ? <Badge variant="outline" className={st.className}>{st.label}</Badge> : null}
                  {run.scope_warning ? (
                    <Badge variant="outline" className="bg-status-warning text-status-warning-foreground border-status-warning-border">
                      Scope warning
                    </Badge>
                  ) : null}
                </div>
                <CardTitle className="font-mono text-base break-all">{run.id}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <div className="text-muted-foreground">Status</div>
                  <div className="text-foreground">{run.status}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Scope warning</div>
                  <div className="text-foreground">{run.scope_warning ? "Yes" : "No"}</div>
                </div>
                <p className="text-muted-foreground pt-2">
                  Detailed tool, target, and log data depends on the API response schema and may be extended in future updates.
                </p>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </RequireAuth>
  );
}
