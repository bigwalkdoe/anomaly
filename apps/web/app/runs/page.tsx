"use client";

import { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { apiJson, Run } from "@/lib/api";
import { Plus, ArrowRight, Play, StopCircle } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRuns = useCallback(async () => {
    try {
      const data = await apiJson<Run[]>("/api/runs?limit=100");
      setRuns(data);
    } catch (err) {
      console.error("Failed to fetch runs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const handleCreateRun = async () => {
    // Quick create run
    try {
      await apiJson("/api/engagements/1/runs", {
        method: "POST",
        body: JSON.stringify({ tool: "nmap", targets: ["example.com"] }),
      });
      fetchRuns();
    } catch (err) {
      console.error("Failed to create run:", err);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Runs</h1>
            <p className="text-muted-foreground">Monitor tool execution runs</p>
          </div>
          <button
            onClick={handleCreateRun}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          >
            <Play className="h-4 w-4" /> New Run
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-card shadow-sm overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">ID</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Tool</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Scope Warning</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {runs.length > 0 ? (
                  runs.map((run) => (
                    <tr key={run.id} className="border-b border-border hover:bg-accent">
                      <td className="px-4 py-3 font-mono text-xs">{run.id.slice(0, 8)}...</td>
                      <td className="px-4 py-3">{run.tool}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${STATUS_COLORS[run.status.toLowerCase()] || "bg-gray-100 text-gray-800"}`}>
                          {run.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {run.scope_warning ? (
                          <span className="text-xs text-orange-600">⚠️ Warning</span>
                        ) : (
                          <span className="text-xs text-green-600">✓ Clean</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button className="rounded-md p-2 text-muted-foreground hover:text-primary transition-colors" title="View details">
                          <ArrowRight className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                )) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-12 text-center">
                      <Play className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <h3 className="text-lg font-semibold">No runs</h3>
                      <p className="text-muted-foreground">Start a tool run to see results here.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
