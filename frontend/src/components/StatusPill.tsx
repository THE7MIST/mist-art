interface StatusPillProps {
  label: string;
  tone?: "neutral" | "ready" | "working" | "warn";
}

export function StatusPill({ label, tone = "neutral" }: StatusPillProps) {
  return <span className={`status-pill status-${tone}`}>{label}</span>;
}
