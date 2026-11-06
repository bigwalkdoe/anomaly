"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { cn } from "@/lib/utils";
import { apiJson } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertCircle,
  Clock,
  FileText,
  Layout,
  Play,
  Plus,
  Shield,
  Target,
} from "@/components/ui/icons";

interface DashboardData {
  engagements: number;
  findings: number;
  runs: number;
  critical: number;
  high: number;
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav />
      <Sidebar />
      <main className="md:ml-64 p-4 pt-6 md:p-8">{children}</main>
    </div>
  );
}

function DashboardContent() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiJson<DashboardData>("/api/dashboard")
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <DashboardShell>
        <div className="flex h-64 items-center justify-center">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            Loading dashboard…
          </div>
        </div>
      </DashboardShell>
    );
  }

  const criticalHigh = (data?.critical ?? 0) + (data?.high ?? 0);
  const statCards = [
    {
      title: "Engagements",
      value: data?.engagements ?? 0,
      description: "Active and tracked scopes",
      icon: Layout,
      tone: "text-primary bg-primary/10 border-primary/15",
    },
    {
      title: "Findings",
      value: data?.findings ?? 0,
      description: "Observed security issues",
      icon: Activity,
      tone: "text-status-info-foreground bg-status-info border-status-info-border",
    },
    {
      title: "Runs",
      value: data?.runs ?? 0,
      description: "Tool executions recorded",
      icon: Play,
      tone: "text-status-success-foreground bg-status-success border-status-success-border",
    },
    {
      title: "Critical / High",
      value: criticalHigh,
      description: "Highest-severity findings",
      icon: AlertCircle,
      tone:
        criticalHigh > 0
          ? "text-status-danger-foreground bg-status-danger border-status-danger-border"
          : "text-muted-foreground bg-muted border-border",
    },
  ];

  return (
    <DashboardShell>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Overview
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Monitor engagements, findings, and execution activity across Anomaly.
          </p>
        </div>
        <Button asChild>
          <Link href="/engagements">
            <Plus className="h-4 w-4" aria-hidden="true" />
            View engagements
          </Link>
        </Button>
      </div>

      {error ? (
        <div
          role="alert"
          className="mb-6 flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium text-foreground">Dashboard data unavailable</p>
            <p className="mt-0.5 text-muted-foreground">{error}</p>
          </div>
        </div>
      ) : null}

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <Card key={card.title} className="overflow-hidden">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
              <div className="space-y-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {card.title}
                </CardTitle>
                <div className="text-2xl font-semibold tracking-tight text-foreground">
                  {card.value}
                </div>
              </div>
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-md border",
                  card.tone
                )}
              >
                <card.icon className="h-4 w-4" aria-hidden="true" />
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-muted-foreground">{card.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recent findings</CardTitle>
            <CardDescription>
              Triage and review security findings across engagements.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-dashed border-border bg-muted/20 p-8">
              <div className="mx-auto flex max-w-sm flex-col items-center text-center">
                <Activity className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
                <p className="mt-3 text-sm text-muted-foreground">
                  Finding details are available from the findings workspace.
                </p>
                <Button asChild size="sm" className="mt-4" variant="outline">
                  <Link href="/findings">Open findings</Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent runs</CardTitle>
              <CardDescription>Execution status and tool activity.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border border-dashed border-border bg-muted/20 p-6 text-center">
                <Clock className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
                <p className="mt-3 text-sm text-muted-foreground">
                  Monitor queued, running, and completed runs.
                </p>
                <Button asChild size="sm" className="mt-4" variant="outline">
                  <Link href="/runs">Open runs</Link>
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
              <CardDescription>Common operator workflows.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2">
                <Button asChild variant="outline" className="justify-start">
                  <Link href="/engagements">
                    <Target className="h-4 w-4" aria-hidden="true" />
                    Engagements
                  </Link>
                </Button>
                <Button asChild variant="outline" className="justify-start">
                  <Link href="/runs">
                    <Play className="h-4 w-4" aria-hidden="true" />
                    Runs
                  </Link>
                </Button>
                <Button asChild variant="outline" className="justify-start">
                  <Link href="/reports">
                    <FileText className="h-4 w-4" aria-hidden="true" />
                    Reports
                  </Link>
                </Button>
                <Button asChild variant="outline" className="justify-start">
                  <Link href="/settings">
                    <Shield className="h-4 w-4" aria-hidden="true" />
                    Settings
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardShell>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <DashboardContent />
    </RequireAuth>
  );
}
