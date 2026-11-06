const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  const cookie = headers["Cookie"];
  return fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
    cache: "no-store",
  });
}

async function fetchApiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetchApi(path, options);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export { fetchApiJson as apiJson };

interface Engagement {
  id: string;
  name: string;
  mode: string;
  status: string;
  owner_id: string;
}

interface Finding {
  id: string;
  engagement_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
}

interface Run {
  id: string;
  engagement_id: string;
  tool: string;
  status: string;
  scope_warning: boolean;
}

interface Stats {
  engagements: number;
  findings: number;
  runs: number;
}

export async function getStats(): Promise<Stats> {
  try {
    return await fetchApiJson<Stats>("/api/stats");
  } catch {
    return { engagements: 0, findings: 0, runs: 0 };
  }
}

export async function getEngagements(): Promise<Engagement[]> {
  try {
    return await fetchApiJson<Engagement[]>("/api/engagements");
  } catch {
    return [];
  }
}

export async function getFindings(engagementId?: string): Promise<Finding[]> {
  try {
    return await fetchApiJson<Finding[]>(`/api/engagements/${engagementId}/findings`);
  } catch {
    return [];
  }
}

export async function getRuns(engagementId?: string): Promise<Run[]> {
  try {
    return await fetchApiJson<Run[]>(`/api/engagements/${engagementId}/runs`);
  } catch {
    return [];
  }
}
