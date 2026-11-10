"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sidebar, TopNav } from "@/components/layout/layout";
import { RequireAuth } from "@/components/RequireAuth";
import { apiJson } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, List, Plus, Trash2 } from "@/components/ui/icons";

interface Engagement { id: string; name: string }
interface StepDraft { name: string; tool: string; order: number }

export default function NewPlaybookPage() {
  const router = useRouter();
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [engagementId, setEngagementId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<StepDraft[]>([{ name: "Step 1", tool: "nmap", order: 0 }]);
  const [loading, setLoading] = useState(false);
  const [loadingEng, setLoadingEng] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<Engagement[]>("/api/engagements")
      .then((data) => { setEngagements(data); if (data[0]) setEngagementId(data[0].id); })
      .catch(() => setEngagements([]))
      .finally(() => setLoadingEng(false));
  }, []);

  const addStep = () => setSteps((s) => [...s, { name: `Step ${s.length + 1}`, tool: "nmap", order: s.length }]);
  const removeStep = (idx: number) => setSteps((s) => s.filter((_, i) => i !== idx).map((st, i) => ({ ...st, order: i })));
  const updateStep = (idx: number, patch: Partial<StepDraft>) => setSteps((s) => s.map((st, i) => i === idx ? { ...st, ...patch } : st));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!engagementId) return;
    setLoading(true);
    setError(null);
    try {
      await apiJson(`/api/engagements/${engagementId}/playbooks`, {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          steps: steps.map((s, i) => ({ name: s.name.trim() || `Step ${i + 1}`, tool: s.tool.trim() || "stub", params: {}, order: i })),
        }),
      });
      router.push("/playbooks");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create playbook");
    } finally {
      setLoading(false);
    }
  };

  return (
    <RequireAuth>
      <div className="min-h-screen bg-background text-foreground">
        <TopNav />
        <Sidebar />
        <main className="md:ml-64 p-4 pt-6 md:p-8">
          <div className="mb-8 space-y-3">
            <Link href="/playbooks" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />Back to playbooks
            </Link>
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Playbooks</p>
              <h1 className="text-2xl font-semibold tracking-tight">New playbook</h1>
              <p className="text-sm text-muted-foreground">Define a multi-step workflow for an engagement.</p>
            </div>
          </div>

          <Card className="max-w-3xl">
            <CardHeader>
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-muted/30 text-primary"><List className="h-4 w-4" aria-hidden="true" /></div>
              <CardTitle>Create playbook</CardTitle>
              <CardDescription>Add steps in execution order. Each step creates a run when executed.</CardDescription>
            </CardHeader>
            <CardContent>
              {error ? <div role="alert" className="mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div> : null}
              <form onSubmit={onSubmit} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="engagement">Engagement</Label>
                  <select id="engagement" required disabled={loadingEng || engagements.length === 0} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={engagementId} onChange={(e) => setEngagementId(e.target.value)}>
                    {engagements.length === 0 ? <option value="">{loadingEng ? "Loading…" : "No engagements"}</option> : engagements.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Web recon workflow" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="desc">Description (optional)</Label>
                  <Input id="desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this playbook does" />
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Steps</Label>
                    <Button type="button" variant="outline" size="sm" onClick={addStep}><Plus className="h-4 w-4" />Add step</Button>
                  </div>
                  <div className="space-y-3">
                    {steps.map((step, idx) => (
                      <div key={idx} className="grid gap-2 rounded-md border border-border p-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
                        <div className="space-y-1">
                          <Label htmlFor={`sname-${idx}`} className="text-xs">Step name</Label>
                          <Input id={`sname-${idx}`} value={step.name} onChange={(e) => updateStep(idx, { name: e.target.value })} />
                        </div>
                        <div className="space-y-1">
                          <Label htmlFor={`stool-${idx}`} className="text-xs">Tool</Label>
                          <Input id={`stool-${idx}`} value={step.tool} onChange={(e) => updateStep(idx, { tool: e.target.value })} />
                        </div>
                        <Button type="button" variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground hover:text-destructive" onClick={() => removeStep(idx)} disabled={steps.length === 1} aria-label="Remove step">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-2">
                  <Button type="submit" loading={loading} disabled={!engagementId || loadingEng}>Create playbook</Button>
                  <Button type="button" variant="outline" asChild><Link href="/playbooks">Cancel</Link></Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </main>
      </div>
    </RequireAuth>
  );
}
