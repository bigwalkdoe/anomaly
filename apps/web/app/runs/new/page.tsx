"use client";

import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Play } from "@/components/ui/icons";

export default function NewRunPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Runs
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">New run</h1>
            <p className="text-sm text-muted-foreground">
              Launch a scoped tool execution.
            </p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
                <Play className="h-4 w-4" aria-hidden="true" />
              </div>
              <CardTitle>Run creation pending</CardTitle>
              <CardDescription>
                The dedicated run creation UI is not wired yet. Start runs from an engagement
                workflow or the API for now.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link href="/runs">Back to runs</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
