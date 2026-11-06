"use client";

import { useState } from "react";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Download, FileText } from "@/components/ui/icons";

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
        `/api/reports/engagements/${encodeURIComponent(engagementId)}/generate?format=${encodeURIComponent(format)}`
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
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Deliverables
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
            <p className="text-sm text-muted-foreground">
              Generate engagement reports from findings and evidence.
            </p>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader>
                <CardTitle>Generate report</CardTitle>
                <CardDescription>
                  Provide an engagement identifier and choose an output format.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {error ? (
                  <div
                    role="alert"
                    className="mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                  >
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span>{error}</span>
                  </div>
                ) : null}
                <form
                  onSubmit={generateReport}
                  className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_180px_auto] sm:items-end"
                >
                  <div className="space-y-2">
                    <Label htmlFor="engagement-id">Engagement ID</Label>
                    <Input
                      id="engagement-id"
                      type="text"
                      required
                      value={engagementId}
                      onChange={(e) => setEngagementId(e.target.value)}
                      placeholder="e.g. 550e8400-e29b-…"
                      autoComplete="off"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="report-format">Format</Label>
                    <select
                      id="report-format"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      value={format}
                      onChange={(e) => setFormat(e.target.value as "markdown" | "html" | "pdf")}
                    >
                      <option value="markdown">Markdown</option>
                      <option value="html">HTML</option>
                      <option value="pdf">PDF</option>
                    </select>
                  </div>
                  <Button type="submit" loading={loading} className="sm:min-w-[150px]">
                    <Download className="h-4 w-4" aria-hidden="true" />
                    {loading ? "Generating" : "Generate"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
                  <FileText className="h-4 w-4" aria-hidden="true" />
                </div>
                <CardTitle>Report templates</CardTitle>
                <CardDescription>
                  Reports are assembled from engagement findings and evidence. Generated output is
                  downloaded to your device.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
