export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiRequest(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("anomaly_token") : null;
  return fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiRequest(path, options);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export interface Engagement {
  id: string;
  name: string;
  mode: string;
  status: string;
  owner_id: string;
  client_name?: string | null;
}

export interface Finding {
  id: string;
  engagement_id: string;
  title: string;
  severity: string;
  status: string;
  description: string;
}

export interface Run {
  id: string;
  engagement_id: string;
  tool: string;
  status: string;
  scope_warning: boolean;
}

export interface Stats {
  engagements: number;
  findings: number;
  runs: number;
  critical?: number;
  high?: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
