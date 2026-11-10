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
import { severityVariant } from "@/components/ui/severity";
import { statusVariant } from "@/components/ui/status";
import { AlertCircle, ArrowLeft } from "@/components/ui/icons";

interface Finding {
  id: string;
  engagement_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
}

const FINDING_STATUSES = ["open", "triaged", "confirmed", "remediated", "false_positive", "accepted_risk", "closed"];

export default function FindingDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const load = () => {
    setLoading(true);
    apiJson<Finding>(`/api/findings/${id}`)
      .then(setFinding)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load finding"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [id]);

  const updateStatus = async (status: string) => {
    if (!finding) return;
    setUpdating(true);
    setError(null);
    try {
      const updated = await apiJson<Finding>(`/api/findings/${id}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      setFinding(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <RequireAuth>
        <div className="min-h-screen bg-background text-foreground">
          <TopNav />
          <Sidebar />
          <main className="md:ml-64 p-4 pt-6 md:p-8 text-sm text-muted-foreground">Loading finding…</main>
        </div>
      </RequireAuth>
    );
  }

  const sev = finding ? severityVariant(finding.severity) : null;
  const st = finding ? statusVariant("finding", finding.status) : null;

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-3">
            <Link
              href="/findings"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to findings
            </Link>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Triage</p>
              <h1 className="text-2xl font-semibold tracking-tight">Finding detail</h1>
            </div>
          </div>

          {!finding ? (
            <Card className="max-w-2xl">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-muted-foreground">
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                </div>
                <CardTitle>Finding unavailable</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">{error || "The requested finding could not be loaded."}</p>
                <Button asChild variant="outline"><Link href="/findings">Back to findings</Link></Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 xl:grid-cols-3">
              <Card className="xl:col-span-2">
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {sev ? <Badge variant="outline" className={sev.className}>{sev.label}</Badge> : null}
                    {st ? <Badge variant="outline" className={st.className}>{st.label}</Badge> : null}
                  </div>
                  <CardTitle>{finding.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <h2 className="text-sm font-medium mb-2">Description</h2>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {finding.description || "No description provided."}
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Details</CardTitle></CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Finding ID</div>
                    <div className="font-mono text-xs break-all">{finding.id}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Engagement</div>
                    <Link href={`/engagements/${finding.engagement_id}`} className="text-primary hover:underline font-mono text-xs break-all">
                      {finding.engagement_id}
                    </Link>
                  </div>
                  <div className="space-y-2 pt-2 border-t border-border">
                    <div className="text-muted-foreground">Update status</div>
                    <div className="flex flex-wrap gap-2">
                      {FINDING_STATUSES.map((s) => (
                        <Button
                          key={s}
                          type="button"
                          variant={s === finding.status ? "default" : "outline"}
                          size="sm"
                          disabled={updating || s === finding.status}
                          onClick={() => void updateStatus(s)}
                        >
                          {s.replace(/_/g, " ")}
                        </Button>
                      ))}
                    </div>
                    {error ? <p className="text-xs text-destructive">{error}</p> : null}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </main>
      </div>
    </RequireAuth>
  );
}
