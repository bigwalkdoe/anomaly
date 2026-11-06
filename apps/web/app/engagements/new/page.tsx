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
import { Target } from "@/components/ui/icons";

export default function NewEngagementPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Engagements
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">New engagement</h1>
            <p className="text-sm text-muted-foreground">
              Define scope and create a tracked engagement.
            </p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary">
                <Target className="h-4 w-4" aria-hidden="true" />
              </div>
              <CardTitle>Creation flow pending</CardTitle>
              <CardDescription>
                The dedicated engagement creation UI is not wired yet. Use the API or existing
                workflows until this form is implemented.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link href="/engagements">Back to engagements</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
