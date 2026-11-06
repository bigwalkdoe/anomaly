"use client";
import { useState, useEffect } from "react";

import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Plus, Play } from "@/components/ui/icons";
import Link from "next/link";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

interface Run {
  id: string;
  engagement_id: string;
  tool: string;
  status: string;
  scope_warning: boolean;
}

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiJson<Run[]>("/api/runs?limit=100")
      .then(setRuns)
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
      <TopNav />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Runs</h1>
            <p className="text-muted-foreground">Monitor tool execution runs</p>
          </div>
          <Button className="ml-auto" asChild>
            <a href="/engagements/new">
              <Plus className="h-4 w-4 mr-2" />
              New Run
            </a>
          </Button>
        </div>

        <div className="rounded-lg border border-input bg-card shadow-sm overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
            </div>
          ) : runs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/6">ID</TableHead>
                  <TableHead className="w-1/6">Tool</TableHead>
                  <TableHead className="w-1/6">Status</TableHead>
                  <TableHead className="w-1/6">Scope Warning</TableHead>
                  <TableHead className="w-1/6 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <TableRow key={run.id} className="border-b border-input/50 hover:bg-accent/50">
                    <TableCell className="font-mono text-xs">{run.id.slice(0, 8)}...</TableCell>
                    <TableCell>{run.tool}</TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[run.status.toLowerCase()] || "bg-gray-100 text-gray-800"}>
                        {run.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {run.scope_warning ? (
                        <span className="text-xs text-orange-600">⚠ Warning</span>
                      ) : (
                        <span className="text-xs text-green-600">✓ Clean</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/runs/${run.id}`} className="p-2 text-muted-foreground hover:text-primary">
                        <span className="relative inline-block">
                          <span className="absolute inset-0 flex items-center">
                            <span className="h-4 w-4" />
                          </span>
                        </span>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="rounded-lg border border-input bg-card p-12 text-center">
              <Play className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold">No runs</h3>
              <p className="text-muted-foreground">Start a tool run to see results here.</p>
              <Button asChild className="mt-4">
                <a href="/engagements/new">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Engagement
                </a>
              </Button>
            </div>
          )}
        </div>
      </main>
      </div>
    </RequireAuth>
  );
}
