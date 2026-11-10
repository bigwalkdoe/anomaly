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
import { severityVariant } from "@/components/ui/severity";
import { statusVariant } from "@/components/ui/status";
import { Activity, AlertCircle, ArrowRight, Filter, Plus } from "@/components/ui/icons";

interface Finding {
  id: string;
  engagement_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
}

interface Engagement {
  id: string;
}

function SeverityBadge({ value }: { value: string }) {
  const variant = severityVariant(value);
  return (
    <Badge variant="outline" className={variant.className}>
      {variant.label}
    </Badge>
  );
}

function FindingStatusBadge({ value }: { value: string }) {
  const variant = statusVariant("finding", value);
  return (
    <Badge variant="outline" className={variant.className}>
      {variant.label}
    </Badge>
  );
}

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const engagements = await apiJson<Engagement[]>("/api/engagements");
        const allFindings: Finding[] = [];
        for (const eng of engagements.slice(0, 20)) {
          try {
            const findingsForEng = await apiJson<Finding[]>(`/api/engagements/${eng.id}/findings`);
            allFindings.push(...findingsForEng.map((f) => ({ ...f, engagement_id: eng.id })));
          } catch {
            // skip
          }
        }
        setFindings(allFindings);
      } catch {
        setFindings([]);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const filteredFindings = findings.filter((f) =>
    f.title.toLowerCase().includes(search.toLowerCase())
  );
  const hasSearchNoResults = findings.length > 0 && filteredFindings.length === 0;

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Triage
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">Findings</h1>
              <p className="text-sm text-muted-foreground">
                Review, prioritize, and track security findings.
              </p>
            </div>
            <Button asChild>
              <Link href="/engagements">
                <Plus className="h-4 w-4" aria-hidden="true" />
                New finding
              </Link>
            </Button>
          </div>

          <div className="rounded-xl border border-border bg-card">
            <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:max-w-sm">
                <Activity
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <Input
                  type="search"
                  placeholder="Search findings…"
                  aria-label="Search findings"
                  className="pl-9"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Filter className="h-4 w-4" aria-hidden="true" />
                <span>All findings</span>
              </div>
            </div>

            {loading ? (
              <div className="flex h-64 items-center justify-center">
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  Loading findings…
                </div>
              </div>
            ) : findings.length === 0 ? (
              <div className="p-8">
                <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-muted/20 py-12 text-center">
                  <AlertCircle className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">No findings</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Start a run to generate findings for review.
                    </p>
                  </div>
                  <Button asChild size="sm" className="mt-2">
                    <Link href="/runs">Start a run</Link>
                  </Button>
                </div>
              </div>
            ) : hasSearchNoResults ? (
              <div className="p-8">
                <div className="rounded-lg border border-dashed border-border bg-muted/20 py-10 text-center">
                  <p className="text-sm text-muted-foreground">
                    No findings match “{search}”.
                  </p>
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredFindings.map((f) => (
                    <TableRow key={f.id}>
                      <TableCell className="font-medium">
                        <Link
                          href={`/findings/${f.id}`}
                          className="text-foreground hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                        >
                          {f.title}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <SeverityBadge value={f.severity} />
                      </TableCell>
                      <TableCell>
                        <FindingStatusBadge value={f.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <Button asChild variant="ghost" size="icon" className="h-8 w-8">
                          <Link href={`/findings/${f.id}`} aria-label={`View ${f.title}`}>
                            <ArrowRight className="h-4 w-4" aria-hidden="true" />
                          </Link>
                        </Button>
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
