"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, List, Play, Plus, Trash2 } from "@/components/ui/icons";

interface Engagement { id: string; name: string }
interface PlaybookStep { id: string; name: string; tool: string; order: number }
interface Playbook { id: string; engagement_id: string; name: string; description?: string | null; steps: PlaybookStep[] }

export default function PlaybooksPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [engagementId, setEngagementId] = useState("");
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const loadPlaybooks = async (eid: string) => {
    if (!eid) { setPlaybooks([]); return; }
    try {
      const data = await apiJson<Playbook[]>(`/api/engagements/${eid}/playbooks`);
      setPlaybooks(data);
      setError(null);
    } catch (e) {
      setPlaybooks([]);
      setError(e instanceof Error ? e.message : "Failed to load playbooks");
    }
  };

  useEffect(() => {
    apiJson<Engagement[]>("/api/engagements")
      .then((data) => {
        setEngagements(data);
        const first = data[0]?.id || "";
        setEngagementId(first);
        return first ? loadPlaybooks(first) : Promise.resolve();
      })
      .catch(() => setEngagements([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (engagementId) void loadPlaybooks(engagementId);
  }, [engagementId]);

  const onDelete = async (id: string) => {
    if (!engagementId || !confirm("Delete this playbook?")) return;
    setBusyId(id);
    try {
      await apiJson(`/api/engagements/${engagementId}/playbooks/${id}`, { method: "DELETE" });
      await loadPlaybooks(engagementId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete playbook");
    } finally {
      setBusyId(null);
    }
  };

  const onExecute = async (id: string) => {
    if (!engagementId) return;
    setBusyId(id);
    try {
      await apiJson(`/api/engagements/${engagementId}/playbooks/${id}/execute`, { method: "POST", body: JSON.stringify({ targets: [] }) });
      setError(null);
      alert("Playbook execution enqueued.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to execute playbook");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Automation</p>
              <h1 className="text-2xl font-semibold tracking-tight">Playbooks</h1>
              <p className="text-sm text-muted-foreground">Multi-step tool workflows scoped to an engagement.</p>
            </div>
            <Button asChild><Link href="/playbooks/new"><Plus className="h-4 w-4" aria-hidden="true" />New playbook</Link></Button>
          </div>

          {error ? <div role="alert" className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div> : null}

          <div className="mb-4 max-w-md">
            <label htmlFor="eng" className="mb-1 block text-sm text-muted-foreground">Engagement</label>
            <select id="eng" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={engagementId} onChange={(e) => setEngagementId(e.target.value)} disabled={loading || engagements.length === 0}>
              {engagements.length === 0 ? <option value="">{loading ? "Loading…" : "No engagements"}</option> : engagements.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>

          {loading ? (
            <div className="rounded-xl border border-border bg-card p-8 text-sm text-muted-foreground">Loading…</div>
          ) : playbooks.length === 0 ? (
            <div className="rounded-xl border border-border bg-card p-8">
              <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 py-12 text-center">
                <List className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
                <div>
                  <h3 className="text-sm font-semibold text-foreground">No playbooks</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Create a playbook for the selected engagement.</p>
                </div>
                <Button asChild size="sm" className="mt-2"><Link href="/playbooks/new">Create playbook</Link></Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-4">
              {playbooks.map((p) => (
                <Card key={p.id}>
                  <CardHeader className="pb-3">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <CardTitle className="text-base">{p.name}</CardTitle>
                        {p.description ? <p className="mt-1 text-sm text-muted-foreground">{p.description}</p> : null}
                        <p className="mt-1 text-xs text-muted-foreground">{p.steps?.length || 0} step(s)</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button type="button" size="sm" variant="outline" onClick={() => void onExecute(p.id)} loading={busyId === p.id}><Play className="h-4 w-4" />Execute</Button>
                        <Button type="button" size="sm" variant="outline" className="text-destructive hover:bg-destructive/10" onClick={() => void onDelete(p.id)} disabled={busyId === p.id}><Trash2 className="h-4 w-4" />Delete</Button>
                      </div>
                    </div>
                  </CardHeader>
                  {p.steps?.length ? (
                    <CardContent className="pt-0">
                      <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
                        {[...p.steps].sort((a,b)=>a.order-b.order).map((s) => (
                          <li key={s.id}><span className="text-foreground font-medium">{s.name}</span> <span className="font-mono text-xs">({s.tool})</span></li>
                        ))}
                      </ol>
                    </CardContent>
                  ) : null}
                </Card>
              ))}
            </div>
          )}
          {!loading && engagements.length === 0 ? <p className="mt-4 text-sm text-muted-foreground flex items-center gap-2"><AlertCircle className="h-4 w-4" /> Create an engagement first to manage playbooks.</p> : null}
        </main>
      </div>
    </RequireAuth>
  );
}
