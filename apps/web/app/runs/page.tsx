import { Navbar } from "@/components/Navbar";
import { getRuns, Run } from "@/lib/api";
import { Plus } from "lucide.react";

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

export default async function RunsPage() {
  const runs = await getRuns();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Runs</h1>
            <p className="text-muted-foreground">Monitor tool execution runs</p>
          </div>
          <button className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4" /> New Run
          </button>
        </div>

        <div className="rounded-lg border border-border bg-white shadow-sm overflow-hidden">
          {runs.length > 0 ? (
            <table className="w-full text-left">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">ID</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Tool</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Scope Warning</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-border hover:bg-accent">
                    <td className="px-4 py-3 font-mono text-xs">{run.id.slice(0, 8)}...</td>
                    <td className="px-4 py-3">{run.tool}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${STATUS_COLORS[run.status.toLowerCase()] || "bg-gray-100 text-gray-800"}`}>
                        {run.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {run.scope_warning ? (
                        <span className="text-xs text-orange-600">⚠ Warning</span>
                      ) : (
                        <span className="text-xs text-green-600">✓ Clean</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <a href={`/runs/${run.id}`} className="text-muted-foreground hover:text-primary">
                        <span className="relative inline-block">
                          <span className="absolute inset-0 flex items-center">
                            <span className="h-4 w-4"></span>
                          </span>
                        </span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="rounded-lg border border-border bg-white p-12 text-center">
              <div className="h-12 w-12 text-muted-foreground mx-auto mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold">No runs</h3>
              <p className="text-muted-foreground">Start a tool run to see results here.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
