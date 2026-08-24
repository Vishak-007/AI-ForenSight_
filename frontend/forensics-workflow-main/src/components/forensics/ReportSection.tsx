import type { ReactNode } from "react";

export function ReportSection({
  index,
  title,
  children,
}: {
  index: number;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-card">
      <header className="flex items-center gap-3 border-b border-border bg-muted px-4 py-3">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-brand-deep font-mono text-xs font-bold text-primary-foreground">
          {index}
        </span>
        <h2 className="label-caps min-w-0 truncate text-foreground">{title}</h2>
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function AiNotice({ children }: { children: ReactNode }) {
  return (
    <p className="label-caps mb-2 inline-flex items-center gap-2 rounded-md border border-ai-border bg-ai px-2 py-1 text-brand-dark">
      {children}
    </p>
  );
}
