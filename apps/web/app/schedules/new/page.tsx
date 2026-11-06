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
import { Clock } from "@/components/ui/icons";

export default function NewSchedulePage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Schedules
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">New schedule</h1>
            <p className="text-sm text-muted-foreground">
              Configure an automated, recurring run.
            </p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
                <Clock className="h-4 w-4" aria-hidden="true" />
              </div>
              <CardTitle>Creation flow pending</CardTitle>
              <CardDescription>
                The schedule creation flow is not implemented in this UI yet. Use the schedules
                list and API for now.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link href="/schedules">Back to schedules</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
