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
import { ArrowLeft, Play } from "@/components/ui/icons";

export default function RunDetailPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-3">
            <Link
              href="/runs"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to runs
            </Link>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Execution
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">Run detail</h1>
              <p className="text-sm text-muted-foreground">
                Inspect execution status, logs, and scope signals.
              </p>
            </div>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-muted-foreground">
                <Play className="h-4 w-4" aria-hidden="true" />
              </div>
              <CardTitle>Detail view pending</CardTitle>
              <CardDescription>
                The run detail view is not fully wired in this UI yet. Monitor runs from the runs
                list and API for now.
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
