"use client";

import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Play } from "@/components/ui/icons"

export default function PlaybooksPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const createPlaybook = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Creating playbook:", name, description);
  };

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background">
      <TopNav />
      <Sidebar />
      <main className="flex-1 md:ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Playbooks</h1>
            <p className="text-muted-foreground">Create and execute multi-step tool workflows</p>
          </div>
          <Button className="ml-auto" asChild>
            <a href="/playbooks/new">
              <Plus className="h-4 w-4 mr-2" />
              New Playbook
            </a>
          </Button>
        </div>

        <div className="rounded-lg border border-input bg-card shadow-sm overflow-hidden p-12 text-center">
          <div className="flex flex-col items-center gap-3">
            <Play className="h-12 w-12 text-muted-foreground" />
            <h3 className="text-lg font-semibold">No playbooks</h3>
            <p className="text-muted-foreground">Create your first playbook to automate tool execution.</p>
            <Button asChild className="mt-4">
              <a href="/playbooks/new">
                <Plus className="h-4 w-4 mr-2" />
                Create Playbook
              </a>
            </Button>
          </div>
        </div>
      </main>
      </div>
    </RequireAuth>
  );
}
