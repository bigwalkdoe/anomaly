"use client";

import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "@/components/ui/icons";

export default function NewSchedulePage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <TopNav />
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold">New Schedule</h1>
            <p className="text-muted-foreground">Schedule an automated tool run.</p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Staging placeholder</CardTitle>
              <CardDescription>
                The schedule creation flow is not implemented in this UI yet. Use the schedules list
                and API for now.
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
