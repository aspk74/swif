import clsx from "clsx";

interface BadgeProps {
  severity: string;
  className?: string;
}

const MAP: Record<string, string> = {
  CRITICAL: "badge-critical",
  HIGH: "badge-high",
  MEDIUM: "badge-medium",
  LOW: "badge-low",
  INFORMATIONAL: "badge-informational",
  // status badges
  AUTOMATED_FIX: "badge-pass",
  LOGGED_FOR_REVIEW: "badge-processing",
  QUARANTINED: "badge-quarantined",
};

const DOT: Record<string, string> = {
  CRITICAL: "pulse-dot pulse-dot-crimson",
  HIGH: "pulse-dot pulse-dot-crimson",
  AUTOMATED_FIX: "pulse-dot pulse-dot-emerald",
  LOGGED_FOR_REVIEW: "pulse-dot pulse-dot-cyan",
};

export function Badge({ severity, className }: BadgeProps) {
  const cls = MAP[severity] || "badge-informational";
  const dot = DOT[severity];
  return (
    <span className={clsx("badge", cls, className)}>
      {dot && <span className={dot} />}
      {severity.replace(/_/g, " ")}
    </span>
  );
}
