"use client";

import { useState } from "react";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Download } from "@/components/ui/icons";

type ReportResponse = {
  content: string;
  engagement_name?: string;
};

export default function ReportsPage() {
  const [engagementId, setEngagementId] = useState("");
  const [format, setFormat] = useState<"markdown" | "html" | "pdf">("markdown");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!engagementId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiJson<ReportResponse>(
        `/api/reports/engagements/${encodeURIComponent(engagementId)}/generate?format=${encodeURIComponent(format)}`,
      );
      const mime =
        format === "html" ? "text/html" : format === "pdf" ? "application/pdf" : "text/markdown";
      const ext = format === "markdown" ? "md" : format;
      const blob = new Blob([data.content ?? ""], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${data.engagement_name || "engagement"}-report.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <TopNav />
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
            {error ? (
              <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            ) : null}
            <form onSubmit={generateReport} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium" htmlFor="engagement-id">
                  Engagement ID
                </label>
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
                <label className="text-sm font-medium" htmlFor="report-format">
                  Format
                </label>
                <select
                  id="report-format"
                  className="rounded-md border border-input bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                  value={format}
                  onChange={(e) => setFormat(e.target.value as "markdown" | "html" | "pdf")}
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
              Reports are generated from engagement findings and evidence. Select an engagement ID
              above to generate a report in your preferred format.
            </p>
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
