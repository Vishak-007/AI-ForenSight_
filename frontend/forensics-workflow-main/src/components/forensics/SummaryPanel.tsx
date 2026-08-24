import { Sparkles, Info } from "lucide-react";

export function SummaryPanel({ summary }: { summary: string }) {
  if (!summary) return null;

  return (
    <section
      aria-label="AI generated case summary"
      className="rounded-xl border-2 border-ai-border bg-ai p-4 shadow-card sm:p-5"
    >
      <h2 className="label-caps flex items-center gap-2 text-brand-dark">
        <Sparkles className="h-4 w-4 text-brand-accent" aria-hidden />
        <span aria-hidden>✦</span> AI-Generated Case Summary
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-foreground sm:text-[0.9375rem]">{summary}</p>
      <p className="mt-4 flex items-start gap-2 border-t border-ai-border pt-3 text-xs text-brand-dark">
        <Info className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />
        AI-generated analysis — verify against source evidence.
      </p>
    </section>
  );
}
