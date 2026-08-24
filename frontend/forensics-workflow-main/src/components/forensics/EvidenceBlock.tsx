import type { ReactNode } from "react";

/** Raw / extracted evidence surface: white background, neutral borders. */
export function EvidenceBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mt-3 rounded-lg border border-evidence-border bg-evidence p-3">
      <p className="label-caps text-muted-foreground">{label}</p>
      <div className="mt-1.5 text-sm leading-relaxed text-foreground">{children}</div>
    </div>
  );
}
