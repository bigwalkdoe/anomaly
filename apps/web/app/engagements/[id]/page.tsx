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
  const [newFindingTitle, setNewFindingTitle] = useState("");
  const [newFindingSeverity, setNewFindingSeverity] = useState("info");
  const [newFindingDescription, setNewFindingDescription] = useState("");
  const [creatingFinding, setCreatingFinding] = useState(false);
  const [scopeIn, setScopeIn] = useState("");
  const [scopeOut, setScopeOut] = useState("");
  const [savingScope, setSavingScope] = useState(false);
  const [targetValue, setTargetValue] = useState("");
  const [targetType, setTargetType] = useState("domain");
  const [addingTarget, setAddingTarget] = useState(false);
  const [editName, setEditName] = useState("");
  const [editStatus, setEditStatus] = useState("draft");
  const [editMode, setEditMode] = useState("own_infra");
  const [editClient, setEditClient] = useState("");
  const [editRoe, setEditRoe] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  // run creation handled via /runs/new

  const fetchData = useCallback(async () => {
    setError(null);
    try {
      const [eng, findingsData, runsData] = await Promise.all([
        apiJson<Engagement>(`/api/engagements/${engagementId}`),
        apiJson<Finding[]>(`/api/engagements/${engagementId}/findings`),
        apiJson<Run[]>(`/api/engagements/${engagementId}/runs`),
      ]);
      setEngagement(eng);
      setEditName(eng.name || "");
      setEditStatus(eng.status || "draft");
      setEditMode(eng.mode || "own_infra");
      setEditClient(eng.client_name || "");
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

  const handleCreateFinding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFindingTitle.trim()) return;
    setCreatingFinding(true);
    setError(null);
    try {
      await apiJson(`/api/engagements/${engagementId}/findings`, {
        method: "POST",
        body: JSON.stringify({
          title: newFindingTitle.trim(),
          severity: newFindingSeverity,
          description: newFindingDescription.trim(),
        }),
      });
      setNewFindingTitle("");
      setNewFindingSeverity("info");
      setNewFindingDescription("");
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create finding");
    } finally {
      setCreatingFinding(false);
    }
  };

  const handleSaveScope = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingScope(true);
    setError(null);
    const entries = [
      ...scopeIn.split(/\n/).map((v) => v.trim()).filter(Boolean).map((target_value) => ({ kind: "in", target_value })),
      ...scopeOut.split(/\n/).map((v) => v.trim()).filter(Boolean).map((target_value) => ({ kind: "out", target_value })),
    ];
    try {
      await apiJson(`/api/engagements/${engagementId}/scope`, {
        method: "PUT",
        body: JSON.stringify({ entries }),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save scope");
    } finally {
      setSavingScope(false);
    }
  };

  const handleAddTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetValue.trim()) return;
    setAddingTarget(true);
    setError(null);
    try {
      await apiJson(`/api/engagements/${engagementId}/targets`, {
        method: "POST",
        body: JSON.stringify({ value: targetValue.trim(), type: targetType }),
      });
      setTargetValue("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add target");
    } finally {
      setAddingTarget(false);
    }
  };

  const handleSaveEngagement = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingEdit(true);
    setError(null);
    try {
      const updated = await apiJson<Engagement>(`/api/engagements/${engagementId}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName.trim(),
          status: editStatus,
          mode: editMode,
          client_name: editClient.trim() || null,
          rules_of_engagement: editRoe.trim() || null,
        }),
      });
      setEngagement(updated);
      setEditOpen(false);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update engagement");
    } finally {
      setSavingEdit(false);
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
              <Button type="button" variant="outline" onClick={() => setEditOpen((v) => !v)}>
                {editOpen ? "Close edit" : "Edit"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleDelete}
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                Delete
              </Button>
              <Button asChild>
                <Link href={`/runs/new?engagementId=${engagement.id}`}>
                  <Play className="h-4 w-4" aria-hidden="true" />
                  New run
                </Link>
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

        {editOpen ? (
          <section className="mb-6 rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold mb-3">Edit engagement</h2>
            <form onSubmit={handleSaveEngagement} className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1 sm:col-span-2">
                <label htmlFor="ename" className="text-xs text-muted-foreground">Name</label>
                <input id="ename" value={editName} onChange={(e) => setEditName(e.target.value)} required className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm" />
              </div>
              <div className="space-y-1">
                <label htmlFor="estatus" className="text-xs text-muted-foreground">Status</label>
                <select id="estatus" value={editStatus} onChange={(e) => setEditStatus(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm">
                  <option value="draft">Draft</option>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                  <option value="completed">Completed</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
              <div className="space-y-1">
                <label htmlFor="emode" className="text-xs text-muted-foreground">Mode</label>
                <select id="emode" value={editMode} onChange={(e) => setEditMode(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm">
                  <option value="own_infra">Own infrastructure</option>
                  <option value="authorized">Authorized testing</option>
                  <option value="bug_bounty">Bug bounty</option>
                  <option value="ctf">CTF / lab</option>
                </select>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label htmlFor="eclient" className="text-xs text-muted-foreground">Client name</label>
                <input id="eclient" value={editClient} onChange={(e) => setEditClient(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm" />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label htmlFor="eroe" className="text-xs text-muted-foreground">Rules of engagement (replaces on save)</label>
                <textarea id="eroe" value={editRoe} onChange={(e) => setEditRoe(e.target.value)} rows={4} className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="Leave blank to keep unchanged on backend if supported; otherwise provide full text." />
              </div>
              <div className="sm:col-span-2 flex gap-2">
                <Button type="submit" loading={savingEdit}>Save changes</Button>
                <Button type="button" variant="outline" onClick={() => setEditOpen(false)}>Cancel</Button>
              </div>
            </form>
          </section>
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
              <div className="border-b border-border p-4 bg-muted/10">
                <form onSubmit={handleCreateFinding} className="grid gap-3 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <label htmlFor="ftitle" className="mb-1 block text-xs text-muted-foreground">Add finding</label>
                    <input
                      id="ftitle"
                      value={newFindingTitle}
                      onChange={(e) => setNewFindingTitle(e.target.value)}
                      placeholder="Finding title"
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      required
                    />
                  </div>
                  <div>
                    <select
                      value={newFindingSeverity}
                      onChange={(e) => setNewFindingSeverity(e.target.value)}
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
                      aria-label="Severity"
                    >
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                      <option value="info">Info</option>
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <textarea
                      value={newFindingDescription}
                      onChange={(e) => setNewFindingDescription(e.target.value)}
                      placeholder="Description (optional)"
                      rows={2}
                      className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <button
                      type="submit"
                      disabled={creatingFinding}
                      className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      {creatingFinding ? "Adding…" : "Add finding"}
                    </button>
                  </div>
                </form>
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
                        <Link
                          href={`/runs/${run.id}`}
                          className="font-medium text-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                        >
                          {(run as { tool?: string }).tool || "Run"} <span className="font-mono text-xs text-muted-foreground">({run.id.slice(0, 8)}…)</span>
                        </Link>
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

          <aside className="space-y-6 xl:col-span-1">
            <div className="rounded-xl border border-border bg-card p-5">
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
                  <dd className="font-mono text-xs text-foreground break-all">{engagement.owner_id}</dd>
                </div>
                {engagement.client_name ? (
                  <div className="flex items-start justify-between gap-4">
                    <dt className="text-muted-foreground">Client</dt>
                    <dd className="text-foreground">{engagement.client_name}</dd>
                  </div>
                ) : null}
              </dl>
            </div>

            <div className="rounded-xl border border-border bg-card p-5">
              <h3 className="text-sm font-semibold">Scope</h3>
              <p className="mt-1 text-xs text-muted-foreground">Replace scope entries (in/out). One value per line.</p>
              <form onSubmit={handleSaveScope} className="mt-3 space-y-3">
                <div>
                  <label htmlFor="scope-in" className="mb-1 block text-xs text-muted-foreground">In scope</label>
                  <textarea id="scope-in" value={scopeIn} onChange={(e) => setScopeIn(e.target.value)} rows={3} className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="example.com" />
                </div>
                <div>
                  <label htmlFor="scope-out" className="mb-1 block text-xs text-muted-foreground">Out of scope</label>
                  <textarea id="scope-out" value={scopeOut} onChange={(e) => setScopeOut(e.target.value)} rows={2} className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="prod.example.com" />
                </div>
                <Button type="submit" size="sm" variant="outline" loading={savingScope}>Save scope</Button>
              </form>
              <form onSubmit={handleAddTarget} className="mt-4 space-y-2 border-t border-border pt-4">
                <p className="text-xs text-muted-foreground">Add target</p>
                <input value={targetValue} onChange={(e) => setTargetValue(e.target.value)} placeholder="Target value" className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm" />
                <select value={targetType} onChange={(e) => setTargetType(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm">
                  <option value="domain">Domain</option>
                  <option value="ip">IP</option>
                  <option value="cidr">CIDR</option>
                  <option value="url">URL</option>
                  <option value="host">Host</option>
                </select>
                <Button type="submit" size="sm" variant="outline" loading={addingTarget} disabled={!targetValue.trim()}>Add target</Button>
              </form>
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
