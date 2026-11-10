"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, Target } from "@/components/ui/icons";

type EngagementResponse = { id: string; name: string };

export default function NewEngagementPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [mode, setMode] = useState("own_infra");
  const [clientName, setClientName] = useState("");
  const [rules, setRules] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const created = await apiJson<EngagementResponse>("/api/engagements", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          mode,
          client_name: clientName.trim() || null,
          rules_of_engagement: rules.trim() || null,
        }),
      });
      router.push(`/engagements/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create engagement");
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
          <div className="mb-8 space-y-3">
            <Link
              href="/engagements"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to engagements
            </Link>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Engagements
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">New engagement</h1>
              <p className="text-sm text-muted-foreground">
                Define the engagement and create a tracked workspace.
              </p>
            </div>
          </div>

          <Card className="max-w-2xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
                <Target className="h-4 w-4" aria-hidden="true" />
              </div>
              <CardTitle>Create engagement</CardTitle>
              <CardDescription>
                Set core details now; you can manage scope, targets, runs, and findings from the engagement.
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
              <form onSubmit={onSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Acme Corp External Assessment"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mode">Mode</Label>
                  <select
                    id="mode"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                  >
                    <option value="own_infra">Own infrastructure</option>
                    <option value="authorized">Authorized testing</option>
                    <option value="bug_bounty">Bug bounty</option>
                    <option value="ctf">CTF / lab</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="client">Client name (optional)</Label>
                  <Input
                    id="client"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="Client or program name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="roe">Rules of engagement (optional)</Label>
                  <textarea
                    id="roe"
                    value={rules}
                    onChange={(e) => setRules(e.target.value)}
                    rows={5}
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Constraints, contacts, allowed techniques, reporting notes…"
                  />
                </div>
                <div className="flex items-center gap-2 pt-2">
                  <Button type="submit" loading={loading}>
                    Create engagement
                  </Button>
                  <Button type="button" variant="outline" asChild>
                    <Link href="/engagements">Cancel</Link>
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
