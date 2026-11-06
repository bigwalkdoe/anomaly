"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { statusVariant } from "@/components/ui/status";
import { Activity, AlertCircle, ArrowRight, Plus, Trash2 } from "@/components/ui/icons";

interface Engagement {
  id: string;
  name: string;
  mode: string;
  status: string;
  owner_id: string;
}

function StatusBadge({
  domain,
  value,
}: {
  domain: "engagement" | "engagement_mode";
  value: string;
}) {
  const variant = statusVariant(domain, value);
  return (
    <Badge variant="outline" className={variant.className}>
      {variant.label}
    </Badge>
  );
}

export default function EngagementsPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEngagements = async (manual = false) => {
    if (manual) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const data = await apiJson<Engagement[]>("/api/engagements");
      setEngagements(data);
    } catch (err) {
      console.error("Failed to fetch engagements:", err);
      setError(err instanceof Error ? err.message : "Failed to load engagements");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadEngagements();
  }, []);

  const filteredEngagements = engagements.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Operations
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">Engagements</h1>
              <p className="text-sm text-muted-foreground">
                Manage scoped penetration testing and security engagements.
              </p>
            </div>
            <Button asChild>
              <Link href="/engagements/new">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New engagement
              </Link>
            </Button>
          </div>

          {error ? (
            <div
              role="alert"
              className="mb-6 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            >
              {error}
            </div>
          ) : null}

          <div className="rounded-xl border border-border bg-card">
            <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:max-w-sm">
                <Activity
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <Input
                  type="search"
                  placeholder="Search engagements…"
                  aria-label="Search engagements"
                  className="pl-9"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void loadEngagements(true)}
                loading={refreshing}
              >
                Refresh
              </Button>
            </div>

            {loading ? (
              <div className="flex h-64 items-center justify-center">
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  Loading engagements…
                </div>
              </div>
            ) : filteredEngagements.length === 0 ? (
              <div className="p-8">
                <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 py-12 text-center">
                  <AlertCircle className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">No engagements found</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {search
                        ? "No engagements match your search."
                        : "Create an engagement to define scope and start work."}
                    </p>
                  </div>
                  {!search ? (
                    <Button asChild size="sm" className="mt-2">
                      <Link href="/engagements/new">Create engagement</Link>
                    </Button>
                  ) : null}
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Mode</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEngagements.map((eng) => (
                    <TableRow key={eng.id}>
                      <TableCell className="font-medium">
                        <Link
                          href={`/engagements/${eng.id}`}
                          className="text-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                        >
                          {eng.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <StatusBadge domain="engagement_mode" value={eng.mode} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge domain="engagement" value={eng.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button asChild variant="ghost" size="icon" className="h-8 w-8">
                            <Link href={`/engagements/${eng.id}`} aria-label={`View ${eng.name}`}>
                              <ArrowRight className="h-4 w-4" aria-hidden="true" />
                            </Link>
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                            aria-label={`Delete ${eng.name}`}
                            title="Delete"
                            disabled
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                          </Button>
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
