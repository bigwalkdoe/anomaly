"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
import { useAuth } from "@/components/AuthContext";
import { apiJson } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  BarChart3,
  Activity,
  Target,
  FileText,
  Clock,
  AlertCircle,
  Play,
  Layout,
  Plus,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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

export default function DashboardPage() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    apiJson<DashboardData>("/api/dashboard")
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
            <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
          </div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Welcome to Anomaly</h1>
          <p className="text-muted-foreground">Please sign in to get started</p>
          <Button asChild className="mt-4">
            <a href="/login">Sign in</a>
          </Button>
        </div>
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
      <TopNav user={{ name: "Admin" }} />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">
              Penetration Testing and Cyber Operations Platform
            </p>
          </div>
          <Button className="ml-auto" asChild>
            <a href="/engagements/new">
              <Plus className="h-4 w-4 mr-2" />
              New Engagement
            </a>
          </Button>
        </div>

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
                      No findings available.
                    </p>
                    <Button asChild size="sm">
                      <a href="/engagements/new">Create Engagement</a>
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
                      No runs available.
                    </p>
                    <Button asChild size="sm">
                      <a href="/runs">View Runs</a>
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
                <Button
                  asChild
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Target className="h-4 w-4 mr-2" />
                  New Engagement
                </Button>
                <Button
                  asChild
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Play className="h-4 w-4 mr-2" />
                  New Run
                </Button>
                <Button
                  asChild
                  className="w-full justify-start"
                  variant="outline"
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Report
                </Button>
                <Button
                  asChild
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Shield className="h-4 w-4 mr-2" />
                  MFA Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}

import { cn } from "@/lib/utils";
import { Shield } from "lucide-react";
