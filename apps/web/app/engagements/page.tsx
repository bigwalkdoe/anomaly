import { Navbar } from "@/components/Navbar";
import { getEngagements, Engagement } from "@/lib/api";
import { Plus, Trash2 } from "lucide.react";
import Link from "next/link";

const MODE_COLORS: Record<string, string> = {
  own_infra: "bg-blue-100 text-blue-800",
  bug_bounty: "bg-yellow-100 text-yellow-800",
  client: "bg-purple-100 text-purple-800",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-blue-100 text-blue-800",
  active: "bg-green-100 text-green-800",
  paused: "bg-yellow-100 text-yellow-800",
  closed: "bg-gray-100 text-gray-800",
};

export default async function EngagementsPage() {
  const engagements = await getEngagements();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Engagements</h1>
            <p className="text-muted-foreground">Manage penetration testing engagements</p>
          </div>
          <a
            href="/engagements/new"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" /> New Engagement
          </a>
        </div>

        {engagements.length === 0 ? (
          <div className="rounded-lg border border-border bg-white p-12 text-center">
            <div className="h-12 w-12 text-muted-foreground mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold">No engagements</h3>
            <p className="text-muted-foreground">Create your first engagement to get started.</p>
            <a
              href="/engagements/new"
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4" /> Create Engagement
            </a>
          </div>
        ) : (
          <div className="rounded-lg border border-border bg-white shadow-sm overflow-hidden">
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
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${MODE_COLORS[eng.mode] || "bg-gray-100 text-gray-800"}`}>
                        {eng.mode.replace("_", " ").toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${STATUS_COLORS[eng.status] || "bg-gray-100 text-gray-800"}`}>
                        {eng.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <a
                        href={`/engagements/${eng.id}`}
                        className="rounded-md p-2 text-muted-foreground hover:text-primary transition-colors"
                        title="View details"
                      >
                        <Trash2 className="h-4 w-4" />
                      </a>
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
