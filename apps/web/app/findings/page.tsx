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
import { Input } from "@/components/ui/input";
import { Activity, AlertCircle, Filter, Plus } from "@/components/ui/icons";
import Link from "next/link";

interface Finding {
  id: string;
  engagement_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-blue-100 text-blue-800",
  info: "bg-gray-100 text-gray-800",
};

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    apiJson<Finding[]>("/api/search?q=")
      .then(data => setFindings(data))
      .catch(() => setFindings([]))
      .finally(() => setLoading(false));
  }, []);

  const filteredFindings = findings.filter((f) =>
    f.title.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
      <TopNav />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Findings</h1>
            <p className="text-muted-foreground">Track and triage security findings</p>
          </div>
          <Button asChild>
            <a href="/engagements/new">
              <Plus className="h-4 w-4 mr-2" />
              New Finding
            </a>
          </Button>
        </div>

        <div className="rounded-lg border border-input bg-card shadow-sm overflow-hidden">
          <div className="p-4 border-b border-input flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search findings..."
                className="flex-1 border-none bg-transparent focus:ring-0 text-sm text-foreground"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Filter className="h-4 w-4 text-muted-foreground" />
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
            </div>
          ) : findings.length === 0 ? (
            <div className="rounded-lg border border-input bg-card p-12 text-center">
              <div className="flex flex-col items-center gap-3 py-8">
                <AlertCircle className="h-12 w-12 text-muted-foreground" />
                <h3 className="text-lg font-semibold">No findings</h3>
                <p className="text-sm text-muted-foreground">Start a run to generate findings.</p>
                <Button asChild className="mt-4">
                  <a href="/runs">Start a Run</a>
                </Button>
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="px-4 py-3 text-sm font-semibold text-muted-foreground text-left">Title</TableHead>
                  <TableHead className="px-4 py-3 text-sm font-semibold text-muted-foreground">Severity</TableHead>
                  <TableHead className="px-4 py-3 text-sm font-semibold text-muted-foreground">Status</TableHead>
                  <TableHead className="px-4 py-3 text-sm font-semibold text-muted-foreground text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredFindings.map((f) => (
                  <TableRow key={f.id} className="border-b border-input/50 hover:bg-accent/50">
                    <TableCell className="font-medium">
                      <Link href={`/findings/${f.id}`} className="hover:text-primary">
                        {f.title}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge className={SEVERITY_COLORS[f.severity.toLowerCase()] || "bg-gray-100 text-gray-800"}>
                        {f.severity.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs font-medium text-muted-foreground">{f.status}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/findings/${f.id}`} className="p-2 text-muted-foreground hover:text-primary">
                        <span className="sr-only">View</span>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </main>
      </div>
    </RequireAuth>
  );
}
