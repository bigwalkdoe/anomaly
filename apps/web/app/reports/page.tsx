"use client";

import { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { apiJson } from "@/lib/api";
import { FileText, Download, AlertTriangle } from "lucide-react";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [engagementId, setEngagementId] = useState("");

  useEffect(() => {
    setLoading(false);
  }, []);

  const generateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!engagementId) return;
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/reports/engagements/${engagementId}/generate?format=markdown`);
      const data = await res.json();
      // Create download link
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
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Reports</h1>
            <p className="text-muted-foreground">Generate engagement reports</p>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card shadow-sm overflow-hidden p-6">
          <h2 className="text-lg font-semibold mb-4">Generate Report</h2>
          <form onSubmit={generateReport} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Engagement ID</label>
              <input
                type="text"
                required
                className="rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                value={engagementId}
                onChange={(e) => setEngagementId(e.target.value)}
                placeholder="e.g. 550e8400-e29b..."
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium">Format</label>
              <select className="rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                <option value="markdown">Markdown</option>
                <option value="html">HTML</option>
                <option value="pdf">PDF</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Download className="h-4 w-4" /> Generate Report
            </button>
          </form>
        </div>

        {loading && (
          <div className="mt-6 flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        )}

        <div className="mt-8 rounded-lg border border-border bg-card p-6">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
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
