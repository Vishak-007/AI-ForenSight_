import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function RecordId({ id, tone = "neutral" }: { id: string; tone?: "neutral" | "red" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-1.5 py-0.5 font-mono text-[11px] font-medium tracking-tight",
        tone === "red"
          ? "border-ai-border bg-ai text-brand-dark"
          : "border-border bg-muted text-muted-foreground",
      )}
    >
      {id}
    </span>
  );
}

export function KindBadge({ kind }: { kind: string }) {
  return (
    <span className="label-caps inline-flex items-center gap-1.5 rounded-md bg-brand-deep px-2 py-1 text-primary-foreground">
      {kind}
    </span>
  );
}

export function SectionLabel({
  icon,
  children,
  right,
}: {
  icon?: ReactNode;
  children: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
      <h2 className="label-caps flex items-center gap-2 text-foreground">
        {icon}
        {children}
      </h2>
      {right}
    </div>
  );
}

export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-card shadow-card",
        className,
      )}
    >
      {children}
    </section>
  );
}
