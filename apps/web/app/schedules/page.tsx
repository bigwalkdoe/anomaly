"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertCircle, Clock, Plus, Trash2 } from "@/components/ui/icons";

interface Engagement { id: string; name: string }
interface Schedule {
  id: string;
  engagement_id: string;
  cron_expression: string;
  tool: string;
  targets: string[];
  is_active: boolean;
  next_run_at: string | null;
}

export default function SchedulesPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [engagementId, setEngagementId] = useState("");
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSchedules = async (eid: string) => {
    if (!eid) { setSchedules([]); return; }
    try {
      const data = await apiJson<Schedule[]>(`/api/engagements/${eid}/schedules`);
      setSchedules(data);
      setError(null);
    } catch (e) {
      setSchedules([]);
      setError(e instanceof Error ? e.message : "Failed to load schedules");
    }
  };

  useEffect(() => {
    apiJson<Engagement[]>("/api/engagements")
      .then((data) => {
        setEngagements(data);
        const first = data[0]?.id || "";
        setEngagementId(first);
        return first ? loadSchedules(first) : Promise.resolve();
      })
      .catch(() => setEngagements([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (engagementId) void loadSchedules(engagementId);
  }, [engagementId]);

  const onDelete = async (id: string) => {
    if (!engagementId || !confirm("Delete this schedule?")) return;
    try {
      await apiJson(`/api/engagements/${engagementId}/schedules/${id}`, { method: "DELETE" });
      await loadSchedules(engagementId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete schedule");
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
              <h1 className="text-2xl font-semibold tracking-tight">Schedules</h1>
              <p className="text-sm text-muted-foreground">Recurring tool runs per engagement (cron-based).</p>
            </div>
            <Button asChild>
              <Link href="/schedules/new"><Plus className="h-4 w-4" aria-hidden="true" />New schedule</Link>
            </Button>
          </div>

          {error ? (
            <div role="alert" className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
          ) : null}

          <div className="mb-4 max-w-md">
            <label htmlFor="eng" className="mb-1 block text-sm text-muted-foreground">Engagement</label>
            <select
              id="eng"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={engagementId}
              onChange={(e) => setEngagementId(e.target.value)}
              disabled={loading || engagements.length === 0}
            >
              {engagements.length === 0 ? <option value="">{loading ? "Loading…" : "No engagements"}</option> : engagements.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>

          <div className="rounded-xl border border-border bg-card">
            {loading ? (
              <div className="p-8 text-sm text-muted-foreground">Loading…</div>
            ) : schedules.length === 0 ? (
              <div className="p-8">
                <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 py-12 text-center">
                  <Clock className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">No schedules</h3>
                    <p className="mt-1 text-sm text-muted-foreground">Create a cron schedule for the selected engagement.</p>
                  </div>
                  <Button asChild size="sm" className="mt-2"><Link href="/schedules/new">Create schedule</Link></Button>
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cron</TableHead>
                    <TableHead>Tool</TableHead>
                    <TableHead>Targets</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {schedules.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-mono text-xs">{s.cron_expression}</TableCell>
                      <TableCell>{s.tool}</TableCell>
                      <TableCell className="text-muted-foreground">{(s.targets || []).join(", ") || "—"}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={s.is_active ? "bg-status-success text-status-success-foreground border-status-success-border" : ""}>
                          {s.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => void onDelete(s.id)} aria-label="Delete schedule">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
          {!loading && engagements.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground flex items-center gap-2"><AlertCircle className="h-4 w-4" /> Create an engagement first to manage schedules.</p>
          ) : null}
        </main>
      </div>
    </RequireAuth>
  );
}
