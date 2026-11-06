"use client";

import Link from "next/link";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "@/components/ui/icons";

export default function NewPlaybookPage() {
  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
        <TopNav />
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold">New Playbook</h1>
            <p className="text-muted-foreground">Create a multi-step tool workflow.</p>
          </div>
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Staging placeholder</CardTitle>
              <CardDescription>
                The playbook creation flow is not implemented in this UI yet. Use the playbook list
                and API for now.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link href="/playbooks">Back to playbooks</Link>
              </Button>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
