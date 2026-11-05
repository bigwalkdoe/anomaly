import { Navbar } from "@/components/Navbar";
import { getFindings, Finding } from "@/lib/api";
import { Plus } from "lucide.react";
import Link from "next/link";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-blue-100 text-blue-800",
  info: "bg-gray-100 text-gray-800",
};

export default async function FindingsPage() {
  const findings = await getFindings();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Findings</h1>
            <p className="text-muted-foreground">Track and triage security findings</p>
          </div>
          <button className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4" /> New Finding
          </button>
        </div>

        <div className="rounded-lg border border-border bg-white shadow-sm overflow-hidden">
          {findings.length === 0 ? (
            <div className="rounded-lg border border-border bg-white p-12 text-center">
              <div className="h-12 w-12 text-muted-foreground mx-auto mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold">No findings</h3>
              <p className="text-muted-foreground">Start a run to generate findings.</p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Title</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Severity</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-sm font-semibold text-muted-foreground text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f) => (
                  <tr key={f.id} className="border-b border-border hover:bg-accent">
                    <td className="px-4 py-3">
                      <Link href={`/findings/${f.id}`} className="font-medium hover:text-primary">
                        {f.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${SEVERITY_COLORS[f.severity.toLowerCase()] || "bg-gray-100 text-gray-800"}`}>
                        {f.severity.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium text-muted-foreground">{f.status}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/findings/${f.id}`} className="text-muted-foreground hover:text-primary">
                        <span className="relative inline-block">
                          <span className="absolute inset-0 flex items-center">
                            <span className="h-4 w-4"></span>
                          </span>
                        </span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
