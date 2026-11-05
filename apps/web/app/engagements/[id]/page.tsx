"use client";

import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
import { useAuth } from "@/components/AuthContext";
import { apiJson } from "@/lib/api";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Play, ArrowRight, Target, Activity, AlertCircle, Trash2 } from "lucide-react";

const MODE_COLORS: Record<string, string> = {
  own_infra: "bg-blue-100 text-blue-800",
  bug_bounty: "bg-yellow-100 text-yellow-800",
  client: "bg-purple-100 text-purple-800",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-800",
  draft: "bg-blue-100 text-blue-800",
  paused: "bg-yellow-100 text-yellow-800",
};

const RUN_STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};


const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-blue-100 text-blue-800",
  info: "bg-gray-100 text-gray-800",
};

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

export default function EngagementDetailPage() {
  const params = useParams();
  const router = useRouter();
  const engagementId = params.id as string;
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [eng, findings, runs] = await Promise.all([
        apiJson<Engagement>(`/api/engagements/${engagementId}`),
        apiJson<Finding[]>(`/api/engagements/${engagementId}/findings`),
        apiJson<Run[]>(`/api/engagements/${engagementId}/runs`),
      ]);
      setEngagement(eng);
      setFindings(findings);
      setRuns(runs);
    } catch (err) {
      console.error("Failed to fetch engagement data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [engagementId]);

  const handleCreateRun = async () => {
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
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this engagement?")) return;
    try {
      await apiJson(`/api/engagements/${engagementId}`, { method: "DELETE" });
      router.push("/engagements");
    } catch (err) {
      console.error("Failed to delete engagement:", err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!engagement) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold">Engagement not found</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <header className="mb-8">
          <Link href="/engagements" className="text-sm text-muted-foreground hover:text-primary">
            ← Back to Engagements
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mt-4">
            <div>
              <h1 className="text-2xl font-bold">{engagement.name}</h1>
              <p className="text-muted-foreground">
                {engagement.mode.replace("_", " ").toUpperCase()} • {engagement.status.toUpperCase()}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDelete}
                className="text-sm text-destructive hover:bg-destructive/10 rounded-md px-3 py-1.5 transition-colors"
              >
                Delete Engagement
              </button>
              <Button
                onClick={handleCreateRun}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
              >
                <Play className="h-4 w-4" /> New Run
              </Button>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <section className="rounded-lg border border-input bg-card p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Findings ({findings.length})</h2>
              <div className="space-y-3">
                {findings.length > 0 ? (
                  findings.map((f) => (
                    <div key={f.id} className="p-3 rounded-md border border-input bg-background">
                      <div className="flex justify-between items-start mb-1">
                        <Link href={`/findings/${f.id}`} className="font-medium hover:text-primary">
                          {f.title}
                        </Link>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_COLORS[f.severity.toLowerCase()] || "bg-gray-100 text-gray-800"}`}>
                          {f.severity.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">{f.description}</p>
                      <span className="text-xs font-medium text-muted-foreground">{f.status}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">No findings yet.</p>
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-lg border border-input bg-card p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Runs ({runs.length})</h2>
              <div className="space-y-3">
                {runs.length > 0 ? (
                  runs.map((run) => (
                    <div key={run.id} className="p-3 rounded-md border border-input bg-background">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium">{run.tool}</span>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${RUN_STATUS_COLORS[run.status.toLowerCase()] || "bg-gray-100 text-gray-800"}`}>
                          {run.status.toUpperCase()}
                        </span>
                      </div>
                      {run.scope_warning && (
                        <span className="text-xs text-orange-600 flex items-center gap-1">
                          ⚠️ Scope warning
                        </span>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground">No runs yet.</p>
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="lg:col-span-1">
            <div className="rounded-lg border border-input bg-card p-6 shadow-sm sticky top-24">
              <h3 className="text-lg font-semibold mb-4">Engagement Details</h3>
              <dl className="space-y-4 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">ID</dt>
                  <dd className="font-mono text-xs">{engagement.id}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Mode</dt>
                  <dd>
                    <Badge className={MODE_COLORS[engagement.mode] || "bg-gray-100 text-gray-800"}>
                      {engagement.mode.replace("_", " ").toUpperCase()}
                    </Badge>
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    <Badge className={STATUS_COLORS[engagement.status.toLowerCase()] || "bg-gray-100 text-gray-800"}>
                      {engagement.status.toUpperCase()}
                    </Badge>
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Owner</dt>
                  <dd className="font-mono text-xs">{engagement.owner_id.slice(0, 8)}...</dd>
                </div>
                {engagement.client_name && (
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Client</dt>
                    <dd>{engagement.client_name}</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

