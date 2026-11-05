"use client";

import { TopNav } from "@/components/layout/layout";
import { Sidebar } from "@/components/layout/layout";
import { useAuth } from "@/components/AuthContext";
import { apiJson } from "@/lib/api";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Play, AlertCircle, Plus } from "lucide-react";
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
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-blue-100 text-blue-800 border-blue-200",
  info: "bg-gray-100 text-gray-800 border-gray-200",
};

export default function FindingsPage() {
  const { token } = useAuth();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiJson<Finding[]>("/api/search?q=")
      .then(setFindings)
      .catch(() => setFindings([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <TopNav user={{ name: "Admin" }} />
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
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : findings.length === 0 ? (
            <div className="rounded-lg border border-input bg-card p-12 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold">No findings</h3>
              <p className="text-muted-foreground">Start a run to generate findings.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/3">Title</TableHead>
                  <TableHead className="w-1/6">Severity</TableHead>
                  <TableHead className="w-1/6">Status</TableHead>
                  <TableHead className="w-1/6 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {findings.map((f) => (
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
          )}
        </div>
      </main>
    </div>
  );
}

