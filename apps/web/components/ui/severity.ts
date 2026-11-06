export type SeverityLevel = "critical" | "high" | "medium" | "low" | "info" | "unknown";

export interface SeverityVariant {
  className: string;
  label: string;
  level: SeverityLevel;
}

const SEVERITY_VARIANTS: Record<SeverityLevel, SeverityVariant> = {
  critical: {
    level: "critical",
    label: "Critical",
    className:
      "bg-severity-critical text-severity-critical-foreground border-severity-critical-border",
  },
  high: {
    level: "high",
    label: "High",
    className:
      "bg-severity-high text-severity-high-foreground border-severity-high-border",
  },
  medium: {
    level: "medium",
    label: "Medium",
    className:
      "bg-severity-medium text-severity-medium-foreground border-severity-medium-border",
  },
  low: {
    level: "low",
    label: "Low",
    className:
      "bg-severity-low text-severity-low-foreground border-severity-low-border",
  },
  info: {
    level: "info",
    label: "Info",
    className:
      "bg-severity-info text-severity-info-foreground border-severity-info-border",
  },
  unknown: {
    level: "unknown",
    label: "Unknown",
    className:
      "bg-severity-unknown text-severity-unknown-foreground border-severity-unknown-border",
  },
};

export function severityVariant(severity: string | null | undefined): SeverityVariant {
  const key = (severity ?? "").toLowerCase().trim() as SeverityLevel;
  return SEVERITY_VARIANTS[key] ?? { ...SEVERITY_VARIANTS.unknown, label: formatLabel(severity) };
}

function formatLabel(value: string | null | undefined): string {
  const raw = (value ?? "").trim();
  if (!raw) return "Unknown";
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
}
