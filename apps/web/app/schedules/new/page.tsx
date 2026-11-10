"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, Clock } from "@/components/ui/icons";

interface Engagement { id: string; name: string }

export default function NewSchedulePage() {
  const router = useRouter();
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [engagementId, setEngagementId] = useState("");
  const [cron, setCron] = useState("0 2 * * *");
  const [tool, setTool] = useState("nmap");
  const [targets, setTargets] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [loadingEng, setLoadingEng] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<Engagement[]>("/api/engagements")
      .then((data) => { setEngagements(data); if (data[0]) setEngagementId(data[0].id); })
      .catch(() => setEngagements([]))
      .finally(() => setLoadingEng(false));
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!engagementId) return;
    setLoading(true);
    setError(null);
    const targetList = targets.split(/[\n,]+/).map((t) => t.trim()).filter(Boolean);
    try {
      await apiJson(`/api/engagements/${engagementId}/schedules`, {
        method: "POST",
        body: JSON.stringify({ cron_expression: cron.trim(), tool: tool.trim(), targets: targetList, params: {}, is_active: isActive }),
      });
      router.push("/schedules");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create schedule");
    } finally {
      setLoading(false);
    }
  };

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-3">
            <Link href="/schedules" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />Back to schedules
            </Link>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Schedules</p>
              <h1 className="text-2xl font-semibold tracking-tight">New schedule</h1>
              <p className="text-sm text-muted-foreground">Create a recurring run for an engagement.</p>
            </div>
          </div>

          <Card className="max-w-2xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary"><Clock className="h-4 w-4" aria-hidden="true" /></div>
              <CardTitle>Create schedule</CardTitle>
              <CardDescription>Define cron expression, tool, and targets. Execution depends on the scheduler/worker.</CardDescription>
            </CardHeader>
            <CardContent>
              {error ? (
                <div role="alert" className="mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /><span>{error}</span>
                </div>
              ) : null}
              <form onSubmit={onSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="engagement">Engagement</Label>
                  <select id="engagement" required disabled={loadingEng || engagements.length === 0} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={engagementId} onChange={(e) => setEngagementId(e.target.value)}>
                    {engagements.length === 0 ? <option value="">{loadingEng ? "Loading…" : "No engagements"}</option> : engagements.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cron">Cron expression</Label>
                  <Input id="cron" required value={cron} onChange={(e) => setCron(e.target.value)} placeholder="0 2 * * *" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tool">Tool</Label>
                  <Input id="tool" required value={tool} onChange={(e) => setTool(e.target.value)} placeholder="nmap" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="targets">Targets</Label>
                  <textarea id="targets" value={targets} onChange={(e) => setTargets(e.target.value)} rows={4} className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder={"example.com"} />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
                  Active
                </label>
                <div className="flex items-center gap-2 pt-2">
                  <Button type="submit" loading={loading} disabled={!engagementId || loadingEng}>Create schedule</Button>
                  <Button type="button" variant="outline" asChild><Link href="/schedules">Cancel</Link></Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
