export type StatusDomain =
  | "run"
  | "finding"
  | "engagement"
  | "engagement_mode"
  | (string & {});

export interface StatusVariant {
  className: string;
  label: string;
  tone: "success" | "warning" | "danger" | "info" | "neutral";
}

const TONE_CLASSES: Record<StatusVariant["tone"], string> = {
  success: "bg-status-success text-status-success-foreground border-status-success-border",
  warning: "bg-status-warning text-status-warning-foreground border-status-warning-border",
  danger: "bg-status-danger text-status-danger-foreground border-status-danger-border",
  info: "bg-status-info text-status-info-foreground border-status-info-border",
  neutral: "bg-status-neutral text-status-neutral-foreground border-status-neutral-border",
};

const DOMAIN_MAP: Record<string, Record<string, StatusVariant["tone"]>> = {
  run: {
    queued: "warning",
    pending: "warning",
    running: "info",
    in_progress: "info",
    processing: "info",
    succeeded: "success",
    success: "success",
    completed: "success",
    failed: "danger",
    error: "danger",
    cancelled: "neutral",
    canceled: "neutral",
  },
  finding: {
    open: "warning",
    new: "warning",
    triaged: "info",
    confirmed: "warning",
    in_progress: "info",
    accepted: "info",
    resolved: "success",
    fixed: "success",
    closed: "neutral",
    ignored: "neutral",
    false_positive: "neutral",
    wont_fix: "neutral",
  },
  engagement: {
    draft: "info",
    planned: "info",
    active: "success",
    running: "success",
    paused: "warning",
    on_hold: "warning",
    completed: "neutral",
    closed: "neutral",
    archived: "neutral",
  },
  engagement_mode: {
    own_infra: "info",
    bug_bounty: "warning",
    client: "neutral",
  },
};

export function statusVariant(
  domain: StatusDomain,
  status: string | null | undefined,
): StatusVariant {
  const key = normalize(status);
  const tone = resolveTone(domain, key);
  return {
    tone,
    className: TONE_CLASSES[tone],
    label: formatStatusLabel(status),
  };
}

function resolveTone(domain: StatusDomain, key: string): StatusVariant["tone"] {
  if (!key) return "neutral";
  const domainMap = DOMAIN_MAP[String(domain)];
  if (domainMap && domainMap[key]) return domainMap[key];

  if (/(succeed|success|complete|pass|active|resolved|fix)/.test(key)) return "success";
  if (/(fail|error|critical|reject)/.test(key)) return "danger";
  if (/(warn|queue|pend|pause|hold|open|new)/.test(key)) return "warning";
  if (/(run|progress|process|draft|triage|info)/.test(key)) return "info";
  return "neutral";
}

function normalize(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function formatStatusLabel(value: string | null | undefined): string {
  const raw = (value ?? "").trim();
  if (!raw) return "Unknown";
  return raw
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
