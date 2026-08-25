import { Check, CircleDashed, Loader2, TriangleAlert } from "lucide-react";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import type { AnalysisStage, AnalysisState } from "@/services/forensics-api";
import { cn } from "@/lib/utils";

function StageIcon({ state }: { state: AnalysisStage["state"] }) {
  if (state === "completed")
    return <Check className="h-4 w-4 text-emerald-600" aria-hidden />;
  if (state === "processing")
    return <Loader2 className="h-4 w-4 animate-spin text-brand-deep" aria-hidden />;
  if (state === "failed")
    return <TriangleAlert className="h-4 w-4 text-brand-accent" aria-hidden />;
  return <CircleDashed className="h-4 w-4 text-muted-foreground" aria-hidden />;
}

export function AnalysisStatusBar({
  progress,
  state,
  message,
}: {
  progress: number;
  state: AnalysisState;
  message?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <span className="label-caps text-foreground">Analysis Progress</span>
        <span className="font-mono text-sm font-bold text-brand-deep">{progress}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Analysis progress"
        className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            state === "failed" ? "bg-brand-accent" : "bg-brand-deep",
          )}
          style={{ width: `${progress}%` }}
        />
      </div>
      <p aria-live="polite" className="mt-2 text-sm text-muted-foreground">
        {state === "running"
          ? (message || "Analysis is running…")
          : state === "completed"
            ? "Analysis complete."
            : state === "failed"
              ? "Analysis failed."
              : "Awaiting analysis."}
      </p>
    </div>
  );
}

export function AnalysisProgress({ stages }: { stages: AnalysisStage[] }) {
  return (
    <Panel>
      <SectionLabel>Pipeline Stages</SectionLabel>
      <ul className="divide-y divide-border">
        {stages.map((stage) => (
          <li
            key={stage.id}
            className={cn(
              "flex items-center gap-3 px-4 py-3",
              stage.state === "processing" && "bg-ai",
            )}
          >
            <StageIcon state={stage.state} />
            <span
              className={cn(
                "min-w-0 flex-1 truncate text-sm",
                stage.state === "pending"
                  ? "text-muted-foreground"
                  : "font-semibold text-foreground",
              )}
            >
              {stage.label}
            </span>
            <span
              className={cn(
                "label-caps shrink-0 rounded-md px-2 py-1",
                stage.state === "completed" && "bg-emerald-50 text-emerald-700",
                stage.state === "processing" && "bg-brand-deep text-primary-foreground",
                stage.state === "pending" && "bg-muted text-muted-foreground",
                stage.state === "failed" && "bg-ai text-brand-dark",
              )}
            >
              {stage.state}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
