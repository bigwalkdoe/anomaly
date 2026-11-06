"use client";

import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function NewRunPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <TopNav />
        <Sidebar />
        <main className="flex-1 md:ml-64 p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold">New Run</h1>
            <p className="text-muted-foreground">Launch a tool run for staging review.</p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Staging placeholder</CardTitle>
              <CardDescription>
                The dedicated run creation flow is not wired in this UI yet. Use an engagement
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
