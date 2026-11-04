"use client";

import { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { apiJson, Stats } from "@/lib/api";
import { BarChart2, Activity, Target, Layout, AlertCircle, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiJson<Stats>("/api/stats")
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  const statCards = [
    { title: "Engagements", value: stats?.engagements ?? 0, icon: Layout, color: "text-blue-600" },
    { title: "Findings", value: stats?.findings ?? 0, icon: Target, color: "text-purple-600" },
    { title: "Runs", value: stats?.runs ?? 0, icon: Activity, color: "text-green-600" },
    { title: "Critical/High", value: ((stats?.critical ?? 0) + (stats?.high ?? 0)), icon: AlertCircle, color: "text-red-600" },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Platform overview</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.title} className="rounded-lg border border-border bg-card p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{card.title}</p>
                  <p className="text-2xl font-bold">{card.value}</p>
                </div>
                <Icon className={`h-5 w-5 ${card.color}`} style={{ color: "currentColor" }} />
              </div>
            </div>
          );
        })}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 rounded-lg border border-border bg-card p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Recent Findings</h2>
              <div className="rounded-md border border-border p-4">
                <p className="text-sm text-muted-foreground">No findings available.</p>
              </div>
            </div>
            <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
              <div className="space-y-3">
                <button className="w-full flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground">
                  <span>New Engagement</span>
                  <Target className="h-4 w-4" />
                </button>
                <button className="w-full flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground">
                  <span>New Run</span>
                  <Activity className="h-4 w-4" />
                </button>
                <button className="w-full flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground">
                  <span>Generate Report</span>
                  <FileText className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

import { FileText } from "lucide-react";
