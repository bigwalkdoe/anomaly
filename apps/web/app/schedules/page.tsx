"use client";

import { Sidebar } from "@/components/layout/layout";
import { TopNav } from "@/components/layout/layout";
import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Play, Plus } from "lucide-react";

export default function SchedulesPage() {
  const [cronExpression, setCronExpression] = useState("");
  const [tool, setTool] = useState("");
  const [targets, setTargets] = useState("");

  const createSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Creating schedule:", cronExpression, tool, targets);
  };

  return (
    <div className="min-h-screen bg-background">
      <TopNav user={{ name: "Admin" }} />
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Schedules</h1>
            <p className="text-muted-foreground">Schedule automated tool runs</p>
          </div>
          <Button className="ml-auto" asChild>
            <a href="/schedules/new">
              <Plus className="h-4 w-4 mr-2" />
              New Schedule
            </a>
          </Button>
        </div>

        <div className="rounded-lg border border-input bg-card shadow-sm overflow-hidden">
          <div className="rounded-md border border-input p-12 text-center">
            <Play className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No schedules</h3>
            <p className="text-muted-foreground">Schedule automated scans to run on a recurring basis.</p>
            <Button asChild className="mt-4">
              <a href="/schedules/new">
                <Plus className="h-4 w-4 mr-2" />
                Create Schedule
              </a>
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
