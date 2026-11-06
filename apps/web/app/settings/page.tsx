"use client";

import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <TopNav />
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-muted-foreground">Account and platform settings.</p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Staging placeholder</CardTitle>
              <CardDescription>
                This area is not fully implemented yet. Core account actions are available from
                authentication flows.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex gap-3">
              <Button asChild variant="outline">
                <Link href="/">Back to dashboard</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/login">Sign in</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
