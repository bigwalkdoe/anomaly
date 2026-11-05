"use client";

import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Download } from "@/components/ui/icons";

export default function ReportsPage() {
  const [engagementId, setEngagementId] = useState("");
  const [loading, setLoading] = useState(false);

  const generateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!engagementId) return;
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/reports/engagements/${engagementId}/generate?format=markdown`);
      const data = await res.json();
      const blob = new Blob([data.content], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${data.engagement_name}-report.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to generate report:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <TopNav user={{ name: "Admin" }} />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Reports</h1>
            <p className="text-muted-foreground">Generate engagement reports</p>
          </div>
        </div>

        <div className="rounded-lg border border-input bg-card shadow-sm overflow-hidden p-6">
          <h2 className="text-lg font-semibold mb-4">Generate Report</h2>
          <form onSubmit={generateReport} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Engagement ID</label>
              <input
                type="text"
                required
                id="engagement-id"
                className="rounded-md border border-input bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                value={engagementId}
                onChange={(e) => setEngagementId(e.target.value)}
                placeholder="e.g. 550e8400-e29b..."
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Format</label>
              <select
                className="rounded-md border border-input bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="markdown">Markdown</option>
                <option value="html">HTML</option>
                <option value="pdf">PDF</option>
              </select>
            </div>
            <Button type="submit" disabled={loading} className="inline-flex items-center gap-2">
              <Download className="h-4 w-4 mr-2" />
              {loading ? "Generating..." : "Generate Report"}
            </Button>
          </form>
        </div>

        <div className="mt-8 rounded-lg border border-input bg-card p-6">
          <div className="flex items-center gap-2">
            <Download className="h-5 w-5 text-orange-500" />
            <h3 className="text-lg font-semibold">Report Templates</h3>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Reports are generated from engagement findings and evidence. Select an engagement ID above to generate a report in your preferred format.
          </p>
        </div>
      </main>
    </div>
  );
}

import { Label } from "@/components/ui/label";
