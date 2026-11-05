import { Navbar } from "@/components/Navbar";
import { getStats } from "@/lib/api";
import { Layout, Target, Activity, AlertCircle } from "lucide-react";

const statCards = [
  { title: "Engagements", icon: Layout, color: "text-blue-600" },
  { title: "Findings", icon: Target, color: "text-purple-600" },
  { title: "Runs", icon: Activity, color: "text-green-600" },
  { title: "Critical/High", icon: AlertCircle, color: "text-red-600" },
];

export default async function DashboardPage() {
  const stats = await getStats();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <h1 className="text-2xl font-bold">Dashboard</h1>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card) => (
            <div key={card.title} className="rounded-lg border border-border bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{card.title}</p>
                  <p className="text-2xl font-bold">{stats[card.title.toLowerCase().replace(/\//g, "")] ?? 0}</p>
                </div>
                <card.icon className={`h-5 w-5 ${card.color}`} />
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 rounded-lg border border-border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Recent Findings</h2>
            <div className="rounded-md border border-border p-4">
              <p className="text-sm text-muted-foreground">No findings available.</p>
            </div>
          </div>
          <div className="rounded-lg border border-border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
            <div className="space-y-3">
              <a href="/engagements" className="w-full flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground">
                <span>View Engagements</span>
                <Target className="h-4 w-4" />
              </a>
              <a href="/runs" className="w-full flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground">
                <span>View Runs</span>
                <Activity className="h-4 w-4" />
              </a>
              <a href="/reports" className="w-full flex items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm text-left transition-colors hover:bg-accent hover:text-accent-foreground">
                <span>Generate Report</span>
                <Target className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
