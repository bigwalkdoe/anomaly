"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "warning"
  | "info"
  | "danger"
  | "neutral"
  | "severity-critical"
  | "severity-high"
  | "severity-medium"
  | "severity-low"
  | "severity-info"
  | "severity-unknown";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variants: Record<BadgeVariant, string> = {
  default: "bg-primary text-primary-foreground border-transparent",
  secondary: "bg-secondary text-secondary-foreground border-transparent",
  destructive: "bg-destructive text-destructive-foreground border-transparent",
  outline: "border-border bg-transparent text-foreground",
  success: "bg-status-success text-status-success-foreground border-status-success-border",
  warning: "bg-status-warning text-status-warning-foreground border-status-warning-border",
  info: "bg-status-info text-status-info-foreground border-status-info-border",
  danger: "bg-status-danger text-status-danger-foreground border-status-danger-border",
  neutral: "bg-status-neutral text-status-neutral-foreground border-status-neutral-border",
  "severity-critical":
    "bg-severity-critical text-severity-critical-foreground border-severity-critical-border",
  "severity-high":
    "bg-severity-high text-severity-high-foreground border-severity-high-border",
  "severity-medium":
    "bg-severity-medium text-severity-medium-foreground border-severity-medium-border",
  "severity-low":
    "bg-severity-low text-severity-low-foreground border-severity-low-border",
  "severity-info":
    "bg-severity-info text-severity-info-foreground border-severity-info-border",
  "severity-unknown":
    "bg-severity-unknown text-severity-unknown-foreground border-severity-unknown-border",
};

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-none",
          variants[variant] ?? variants.default,
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge };
export type { BadgeProps, BadgeVariant };
