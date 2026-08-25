import { Sparkles } from "lucide-react";
import { text } from "@/lib/report-types";

export function AiCaption({ caption, status }: { caption?: string | null | undefined; status?: string | null | undefined }) {
  const value = text(caption);
  if (!value) return null;
  const statusLabel = text(status, "unverified").toUpperCase();

  return (
    <div className="mt-3 rounded-lg border-2 border-ai-border bg-ai p-3">
      <p className="label-caps flex items-center gap-1.5 text-brand-dark">
        <Sparkles className="h-3.5 w-3.5 text-brand-accent" aria-hidden />
        <span aria-hidden>✦</span> AI Caption — {statusLabel}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-foreground">{value}</p>
      <p className="mt-2 text-xs text-brand-dark">AI-generated content. Not verified.</p>
    </div>
  );
}
