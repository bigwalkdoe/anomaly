"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, Play } from "@/components/ui/icons";

interface Engagement {
  id: string;
  name: string;
}

interface RunResponse {
  id: string;
}

function NewRunForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const presetEngagement = searchParams.get("engagementId") || "";
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [engagementId, setEngagementId] = useState(presetEngagement);
  const [tool, setTool] = useState("nmap");
  const [targets, setTargets] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingEng, setLoadingEng] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<Engagement[]>("/api/engagements")
      .then((data) => {
        setEngagements(data);
        const preferred = presetEngagement && data.some((e) => e.id === presetEngagement) ? presetEngagement : data[0]?.id || "";
        if (preferred) setEngagementId(preferred);
      })
      .catch(() => setEngagements([]))
      .finally(() => setLoadingEng(false));
  }, [presetEngagement]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!engagementId) return;
    setLoading(true);
    setError(null);
    const targetList = targets
      .split(/[\n,]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      const run = await apiJson<RunResponse>(`/api/engagements/${engagementId}/runs`, {
        method: "POST",
        body: JSON.stringify({ tool: tool.trim() || "stub", targets: targetList, params: {} }),
      });
      router.push(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create run");
    } finally {
      setLoading(false);
    }
  };

  return (
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
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Runs</p>
            <h1 className="text-2xl font-semibold tracking-tight">New run</h1>
            <p className="text-sm text-muted-foreground">Enqueue a tool run within an engagement scope.</p>
          </div>
        </div>

        <Card className="max-w-2xl">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
              <Play className="h-4 w-4" aria-hidden="true" />
            </div>
            <CardTitle>Create run</CardTitle>
            <CardDescription>Select an engagement, choose a tool, and provide targets (one per line or comma-separated).</CardDescription>
          </CardHeader>
          <CardContent>
            {error ? (
              <div role="alert" className="mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            ) : null}
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="engagement">Engagement</Label>
                <select
                  id="engagement"
                  required
                  disabled={loadingEng || engagements.length === 0}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
                  value={engagementId}
                  onChange={(e) => setEngagementId(e.target.value)}
                >
                  {engagements.length === 0 ? (
                    <option value="">{loadingEng ? "Loading…" : "No engagements available"}</option>
                  ) : (
                    engagements.map((e) => (
                      <option key={e.id} value={e.id}>{e.name}</option>
                    ))
                  )}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="tool">Tool</Label>
                <Input id="tool" value={tool} onChange={(e) => setTool(e.target.value)} placeholder="e.g. nmap, nuclei, httpx" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="targets">Targets</Label>
                <textarea
                  id="targets"
                  value={targets}
                  onChange={(e) => setTargets(e.target.value)}
                  rows={5}
                  className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder={"example.com\n10.0.0.1"}
                />
                <p className="text-xs text-muted-foreground">Targets are scope-checked by the backend; out-of-scope targets are recorded with warnings.</p>
              </div>
              <div className="flex items-center gap-2 pt-2">
                <Button type="submit" loading={loading} disabled={!engagementId || loadingEng}>Create run</Button>
                <Button type="button" variant="outline" asChild><Link href="/runs">Cancel</Link></Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

export default function NewRunPage() {
  return (
    <RequireAuth>
      <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>}>
        <NewRunForm />
      </Suspense>
    </RequireAuth>
  );
}
