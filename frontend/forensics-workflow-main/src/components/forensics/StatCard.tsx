import type { ReactNode } from "react";

export function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-card">
      <div className="flex items-center gap-2 text-brand-deep">
        {icon}
        <span className="label-caps text-muted-foreground">{label}</span>
      </div>
      <p className="mt-2 truncate font-mono text-xl font-bold text-foreground">{value}</p>
      {hint && <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
