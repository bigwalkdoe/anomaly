"use client";
import Link from "next/link";

import { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/Navbar";
import { apiJson, Engagement } from "@/lib/api";
import { Plus, Trash2, Edit2, ArrowRight, Menu } from "lucide-react";

export default function EngagementsPage() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newMode, setNewMode] = useState("own_infra");

  const fetchEngagements = useCallback(async () => {
    try {
      const data = await apiJson<Engagement[]>("/api/engagements");
      setEngagements(data);
    } catch (err) {
      console.error("Failed to fetch engagements:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEngagements();
  }, [fetchEngagements]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiJson("/api/engagements", {
        method: "POST",
        body: JSON.stringify({ name: newName, mode: newMode }),
      });
      setShowCreate(false);
      setNewName("");
      setNewMode("own_infra");
      fetchEngagements();
    } catch (err) {
      console.error("Failed to create engagement:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this engagement?")) return;
    try {
      await apiJson(`/api/engagements/${id}`, { method: "DELETE" });
      fetchEngagements();
    } catch (err) {
      console.error("Failed to delete engagement:", err);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Engagements</h1>
            <p className="text-muted-foreground">Manage penetration testing engagements</p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New Engagement
          </button>
        </div>

        {showCreate && (
          <div className="rounded-lg border border-border bg-card p-6 shadow-sm mb-6">
            <h3 className="text-lg font-semibold mb-4">Create Engagement</h3>
            <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">Name</label>
                <input
                  type="text"
                  required
                  className="rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Internal Network Assessment"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">Mode</label>
                <select
                  className="rounded-md border border-border bg-input px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                  value={newMode}
                  onChange={(e) => setNewMode(e.target.value)}
                >
                  <option value="own_infra">Own Infrastructure</option>
                  <option value="bug_bounty">Bug Bounty</option>
                  <option value="client">Client Engagement</option>
                </select>
              </div>
              <button type="submit" className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
                Create
              </button>
            </form>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : engagements.length === 0 ? (
          <div className="rounded-lg border border-border bg-card p-12 text-center">
            <Menu className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold">No engagements</h3>
            <p className="text-muted-foreground">Create your first engagement to get started.</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4" /> Create Engagement
            </button>
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-card shadow-sm overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Name</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Mode</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {engagements.map((eng) => (
                  <tr key={eng.id} className="border-b border-border hover:bg-accent">
                    <td className="px-4 py-3">
                      <Link href={`/engagements/${eng.id}`} className="font-medium hover:text-primary">
                        {eng.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                        eng.mode === "own_infra" ? "bg-blue-100 text-blue-800" :
                        eng.mode === "bug_bounty" ? "bg-yellow-100 text-yellow-800" :
                        "bg-purple-100 text-purple-800"
                      }`}>
                        {eng.mode.replace("_", " ").toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                        eng.status === "active" ? "bg-green-100 text-green-800" :
                        eng.status === "closed" ? "bg-gray-100 text-gray-800" :
                        "bg-blue-100 text-blue-800"
                      }`}>
                        {eng.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleDelete(eng.id)}
                          className="rounded-md p-2 text-destructive hover:bg-red-50 hover:text-red-600 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}

