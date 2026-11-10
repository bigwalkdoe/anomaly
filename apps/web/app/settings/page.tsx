"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { API_BASE_URL, apiJson } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Settings } from "@/components/ui/icons";

interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
}

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<User>("/api/auth/me")
      .then(setUser)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"));
  }, []);

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Account</p>
            <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
            <p className="text-sm text-muted-foreground">Account and platform context for this session.</p>
          </div>

          <div className="grid gap-6 max-w-3xl">
            <Card>
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                </div>
                <CardTitle>Profile</CardTitle>
                <CardDescription>Current authenticated user (from <code className="text-xs">/api/auth/me</code>).</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {error ? <p className="text-destructive">{error}</p> : null}
                {user ? (
                  <>
                    <div><span className="text-muted-foreground">Name:</span> <span className="font-medium">{user.name}</span></div>
                    <div><span className="text-muted-foreground">Email:</span> <span className="font-medium">{user.email}</span></div>
                    <div className="font-mono text-xs text-muted-foreground break-all"><span className="text-muted-foreground font-sans text-sm">ID:</span> {user.id}</div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-muted-foreground">Roles:</span>
                      {user.roles?.length ? user.roles.map((r) => (
                        <Badge key={r} variant="outline">{r}</Badge>
                      )) : <span className="text-muted-foreground">None</span>}
                    </div>
                  </>
                ) : !error ? (
                  <p className="text-muted-foreground">Loading profile…</p>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Platform</CardTitle>
                <CardDescription>Frontend configuration and quick links.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <div className="text-muted-foreground">API base URL</div>
                  <div className="font-mono text-xs break-all">{API_BASE_URL}</div>
                </div>
                <div className="flex flex-wrap gap-2 pt-2">
                  <Button asChild variant="outline"><Link href="/">Dashboard</Link></Button>
                  <Button asChild variant="outline"><Link href="/engagements">Engagements</Link></Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
