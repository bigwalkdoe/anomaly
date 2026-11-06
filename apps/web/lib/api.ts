const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "anomaly_token";
const REFRESH_KEY = "anomaly_refresh_token";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const data = await fetchApiJson<TokenResponse>("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (data.refresh_token) {
      localStorage.setItem(REFRESH_KEY, data.refresh_token);
    }
    return data.access_token;
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    return null;
  }
}

async function fetchApi(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(options.headers);
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const init: RequestInit = { ...options, headers, cache: "no-store" };
  let res = await fetch(`${API_BASE_URL}${path}`, init);

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = new Headers(options.headers);
      retryHeaders.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: retryHeaders,
        cache: "no-store",
      });
    }
  }

  return res;
}

async function fetchApiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetchApi(path, options);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail =
      typeof error?.detail === "string"
        ? error.detail
        : Array.isArray(error?.detail)
          ? error.detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join(", ")
          : null;
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export { fetchApiJson as apiJson, API_BASE_URL };

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
  if (!engagementId) return [];
  try {
    return await fetchApiJson<Finding[]>(`/api/engagements/${engagementId}/findings`);
  } catch {
    return [];
  }
}

export async function getRuns(engagementId?: string): Promise<Run[]> {
  if (!engagementId) return [];
  try {
    return await fetchApiJson<Run[]>(`/api/engagements/${engagementId}/runs`);
  } catch {
    return [];
  }
}
