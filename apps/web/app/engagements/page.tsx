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
import { Plus, Target, Activity, AlertCircle, Trash2, Loader2 } from "@/components/ui/icons";
import Link from "next/link";

interface Engagement {
  id: string;
  name: string;
  mode: string;
  status: string;
  owner_id: string;
}

const MODE_COLORS: Record<string, string> = {
  own_infra: "bg-blue-100 text-blue-800",
  bug_bounty: "bg-yellow-100 text-yellow-800",
  client: "bg-purple-100 text-purple-800",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-blue-100 text-blue-800",
  active: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  closed: "bg-gray-100 text-gray-800",
};

export default function EngagementsPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const loadEngagements = async () => {
    try {
      const data = await apiJson<Engagement[]>("/api/engagements");
      setEngagements(data);
    } catch (err) {
      console.error("Failed to fetch engagements:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEngagements();
  }, []);

  const filteredEngagements = engagements.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
      <TopNav />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Engagements</h1>
            <p className="text-muted-foreground">
              Manage penetration testing engagements
            </p>
          </div>
          <Button asChild>
            <a href="/engagements/new">
              <Plus className="h-4 w-4 mr-2" />
              New Engagement
            </a>
          </Button>
        </div>

        <div className="rounded-lg border border-input bg-card shadow-sm overflow-hidden">
          <div className="p-4 border-b border-input flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search engagements..."
                className="flex-1 border-none bg-transparent focus:ring-0 text-sm text-foreground"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={loadEngagements}
                disabled={refreshing}
                size="sm"
              >
                <Loader2 className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
            </div>
          ) : filteredEngagements.length === 0 ? (
            <div className="rounded-lg border border-input bg-card p-12 text-center">
              <div className="flex flex-col items-center gap-3 py-8">
                <AlertCircle className="h-12 w-12 text-muted-foreground" />
                <h3 className="text-lg font-semibold">No engagements found</h3>
                <p className="text-sm text-muted-foreground">
                  {search ? "No engagements match your search." : "No engagements found."}
                </p>
                <Button asChild className="mt-4">
                  <a href="/engagements/new">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Engagement
                  </a>
                </Button>
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/3">Name</TableHead>
                  <TableHead className="w-1/6">Mode</TableHead>
                  <TableHead className="w-1/6">Status</TableHead>
                  <TableHead className="w-1/6 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEngagements.map((eng) => (
                  <TableRow key={eng.id} className="hover:bg-accent/50">
                    <TableCell className="font-medium">
                      <Link href={`/engagements/${eng.id}`} className="hover:text-primary">
                        {eng.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge className={MODE_COLORS[eng.mode] || "bg-gray-100 text-gray-800"}>
                        {eng.mode.replace("_", " ").toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[eng.status] || "bg-gray-100 text-gray-800"}>
                        {eng.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link href={`/engagements/${eng.id}`} className="p-2 text-muted-foreground hover:text-primary">
                          <span className="sr-only">View</span>
                        </Link>
                        <button className="p-2 text-destructive hover:bg-destructive/50 hover:text-destructive transition-colors" title="Delete">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
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
