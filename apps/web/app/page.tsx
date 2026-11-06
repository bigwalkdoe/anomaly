"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
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
  Target,
  FileText,
  Clock,
  AlertCircle,
  Play,
  Layout,
  Plus,
  Shield,
} from "@/components/ui/icons";

interface StatCard {
  title: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
}

interface DashboardData {
  engagements: number;
  findings: number;
  runs: number;
  critical: number;
  high: number;
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
      <div className="min-h-screen bg-background">
        <TopNav />
        <Sidebar />
        <main className="flex-1 md:ml-64 p-8">
          <div className="flex items-center justify-center h-64">
            <div className="flex flex-col items-center gap-4">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
              </div>
              <p className="text-muted-foreground">Loading dashboard...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const statCards: StatCard[] = [
    {
      title: "Engagements",
      value: data?.engagements ?? 0,
      icon: Layout,
      color: "text-blue-600 bg-blue-50",
    },
    {
      title: "Findings",
      value: data?.findings ?? 0,
      icon: Activity,
      color: "text-purple-600 bg-purple-50",
    },
    {
      title: "Runs",
      value: data?.runs ?? 0,
      icon: Play,
      color: "text-green-600 bg-green-50",
    },
    {
      title: "Critical / High",
      value: (data?.critical ?? 0) + (data?.high ?? 0),
      icon: AlertCircle,
      color: "text-red-600 bg-red-50",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <TopNav />
      <Sidebar />
      <main className="flex-1 md:ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">
              Penetration Testing and Cyber Operations Platform
            </p>
          </div>
          <Button asChild>
            <Link href="/engagements">
              <Plus className="h-4 w-4 mr-2" />
              Engagements
            </Link>
          </Button>
        </div>

        {error ? (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card) => (
            <Card key={card.title} className="border-b-4 border-b-transparent">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
                <card.icon className={cn("h-4 w-4", card.color)} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{card.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Recent Findings</CardTitle>
              <CardDescription>
                Latest security findings across all engagements
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border border-input p-4">
                <div className="flex items-center justify-center h-48">
                  <div className="flex flex-col items-center gap-3">
                    <Activity className="h-12 w-12 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      Open Findings to review results.
                    </p>
                    <Button asChild size="sm">
                      <Link href="/findings">View Findings</Link>
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Runs</CardTitle>
              <CardDescription>Latest tool execution runs</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border border-input p-4">
                <div className="flex items-center justify-center h-48">
                  <div className="flex flex-col items-center gap-3">
                    <Clock className="h-12 w-12 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      Open Runs to monitor execution.
                    </p>
                    <Button asChild size="sm">
                      <Link href="/runs">View Runs</Link>
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Button asChild className="w-full justify-start" variant="outline">
                  <Link href="/engagements">
                    <Target className="h-4 w-4 mr-2" />
                    Engagements
                  </Link>
                </Button>
                <Button asChild className="w-full justify-start" variant="outline">
                  <Link href="/runs">
                    <Play className="h-4 w-4 mr-2" />
                    Runs
                  </Link>
                </Button>
                <Button asChild className="w-full justify-start" variant="outline">
                  <Link href="/reports">
                    <FileText className="h-4 w-4 mr-2" />
                    Reports
                  </Link>
                </Button>
                <Button asChild className="w-full justify-start" variant="outline">
                  <Link href="/settings">
                    <Shield className="h-4 w-4 mr-2" />
                    Settings
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <DashboardContent />
    </RequireAuth>
  );
}
