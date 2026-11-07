"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { severityVariant } from "@/components/ui/severity";
import { statusVariant } from "@/components/ui/status";
import { AlertCircle, ArrowLeft, Play, Trash2 } from "@/components/ui/icons";

interface Engagement {
  id: string;
  name: string;
  mode: string;
  status: string;
  owner_id: string;
  client_name?: string | null;
}

interface Finding {
  id: string;
  engagement_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
}

interface Run {
  id: string;
  engagement_id: string;
  tool: string;
  status: string;
  scope_warning: boolean;
}

function SemanticBadge({
  domain,
  value,
}: {
  domain: "engagement" | "engagement_mode" | "run" | "finding";
  value: string;
}) {
  const variant = statusVariant(domain, value);
  return (
    <Badge variant="outline" className={variant.className}>
      {variant.label}
    </Badge>
  );
}

function SeverityBadge({ value }: { value: string }) {
  const variant = severityVariant(value);
  return (
    <Badge variant="outline" className={variant.className}>
      {variant.label}
    </Badge>
  );
}

function EngagementDetailContent() {
  const params = useParams();
  const router = useRouter();
  const engagementId = params.id as string;
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingRun, setCreatingRun] = useState(false);

  const fetchData = useCallback(async () => {
    setError(null);
    try {
      const [eng, findingsData, runsData] = await Promise.all([
        apiJson<Engagement>(`/api/engagements/${engagementId}`),
        apiJson<Finding[]>(`/api/engagements/${engagementId}/findings`),
        apiJson<Run[]>(`/api/engagements/${engagementId}/runs`),
      ]);
      setEngagement(eng);
      setFindings(findingsData);
      setRuns(runsData);
    } catch (err) {
      console.error("Failed to fetch engagement data:", err);
      setError(err instanceof Error ? err.message : "Failed to load engagement");
    } finally {
      setLoading(false);
    }
  }, [engagementId]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleCreateRun = async () => {
    setCreatingRun(true);
    try {
      await apiJson(`/api/engagements/${engagementId}/runs`, {
        method: "POST",
        body: JSON.stringify({ tool: "nmap", targets: [] }),
      });
      setRuns([]);
      setLoading(true);
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (err) {
      console.error("Failed to create run:", err);
      setError(err instanceof Error ? err.message : "Failed to create run");
      setCreatingRun(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this engagement?")) return;
    try {
      await apiJson(`/api/engagements/${engagementId}`, { method: "DELETE" });
      router.push("/engagements");
    } catch (err) {
      console.error("Failed to delete engagement:", err);
      setError(err instanceof Error ? err.message : "Failed to delete engagement");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading engagement…
        </div>
      </div>
    );
  }

  if (!engagement) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mx-auto max-w-lg rounded-xl border border-border bg-card p-8 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-muted-foreground" aria-hidden="true" />
            <h1 className="mt-4 text-lg font-semibold">Engagement not found</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {error || "The requested engagement could not be loaded."}
            </p>
            <Button asChild variant="outline" className="mt-5">
              <Link href="/engagements">Back to engagements</Link>
            </Button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav />
      <Sidebar />
      <main className="md:ml-64 p-4 pt-6 md:p-8">
        <header className="mb-8">
          <Link
            href="/engagements"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to engagements
          </Link>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <SemanticBadge domain="engagement_mode" value={engagement.mode} />
                <SemanticBadge domain="engagement" value={engagement.status} />
              </div>
              <h1 className="text-2xl font-semibold tracking-tight">{engagement.name}</h1>
              <p className="text-sm text-muted-foreground font-mono">{engagement.id}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleDelete}
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete
              </Button>
              <Button type="button" onClick={handleCreateRun} loading={creatingRun}>
                <Play className="h-4 w-4" aria-hidden="true" />
                New run
              </Button>
            </div>
          </div>
        </header>

        {error ? (
          <div
            role="alert"
            className="mb-6 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            {error}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <section className="rounded-xl border border-border bg-card">
              <div className="border-b border-border px-5 py-4">
                <h2 className="text-sm font-semibold">Findings</h2>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {findings.length} recorded finding{findings.length === 1 ? "" : "s"}
                </p>
              </div>
              <div className="divide-y divide-border">
                {findings.length > 0 ? (
                  findings.map((f) => (
                    <div key={f.id} className="px-5 py-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 space-y-1">
                          <Link
                            href={`/findings/${f.id}`}
                            className="font-medium text-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                          >
                            {f.title}
                          </Link>
                          <p className="text-sm text-muted-foreground">{f.description}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <SeverityBadge value={f.severity} />
                          <SemanticBadge domain="finding" value={f.status} />
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                    No findings recorded for this engagement yet.
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-card">
              <div className="border-b border-border px-5 py-4">
                <h2 className="text-sm font-semibold">Runs</h2>
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {runs.length} execution{runs.length === 1 ? "" : "s"}
                </p>
              </div>
              <div className="divide-y divide-border">
                {runs.length > 0 ? (
                  runs.map((run) => (
                    <div key={run.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                      <div className="space-y-1">
                        <p className="font-medium text-foreground">{run.tool}</p>
                        {run.scope_warning ? (
                          <p className="flex items-center gap-1.5 text-xs text-status-warning-foreground">
                            <span
                              className="inline-block h-1.5 w-1.5 rounded-full bg-status-warning-foreground"
                              aria-hidden="true"
                            />
                            Scope warning recorded
                          </p>
                        ) : null}
                      </div>
                      <SemanticBadge domain="run" value={run.status} />
                    </div>
                  ))
                ) : (
                  <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                    No runs recorded for this engagement yet.
                  </div>
                )}
              </div>
            </section>
          </div>

          <aside className="xl:col-span-1">
            <div className="rounded-xl border border-border bg-card p-5 xl:sticky xl:top-24">
              <h3 className="text-sm font-semibold">Details</h3>
              <dl className="mt-4 space-y-4 text-sm">
                <div className="flex items-start justify-between gap-4">
                  <dt className="text-muted-foreground">Mode</dt>
                  <dd><SemanticBadge domain="engagement_mode" value={engagement.mode} /></dd>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd><SemanticBadge domain="engagement" value={engagement.status} /></dd>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <dt className="text-muted-foreground">Owner</dt>
                  <dd className="font-mono text-xs text-foreground">{engagement.owner_id}</dd>
                </div>
                {engagement.client_name ? (
                  <div className="flex items-start justify-between gap-4">
                    <dt className="text-muted-foreground">Client</dt>
                    <dd className="text-foreground">{engagement.client_name}</dd>
                  </div>
                ) : null}
              </dl>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default function EngagementDetailPage() {
  return (
    <RequireAuth>
      <EngagementDetailContent />
    </RequireAuth>
  );
}
