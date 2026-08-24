import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Info } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Panel, RecordId } from "@/components/forensics/primitives";
import { useReport } from "@/lib/use-report";
import { list, text } from "@/lib/report-types";

const title = "Analysis Flags — Evidence Examiner Desk";
const description =
  "AI and analysis-derived flags with reasons, sources and related evidence record IDs. Flags are analysis, not confirmed facts.";

export const Route = createFileRoute("/_shell/flags")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: FlagsPage,
});

function FlagsPage() {
  const report = useReport();

  return (
    <>
      <PageHeader
        title="Analysis Flags"
        description="Automatically derived indicators requiring examiner verification."
      />

      <p className="mb-5 flex items-start gap-2 rounded-xl border-2 border-ai-border bg-ai px-4 py-3 text-sm text-brand-dark">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>
          <span className="label-caps block">⚠ Analysis-derived content</span>
          These flags are produced by automated analysis. They are indicators only and must be
          verified against the raw evidence before being treated as fact.
        </span>
      </p>

      {report.flags.length === 0 ? (
        <Panel>
          <p className="px-4 py-12 text-center text-sm text-muted-foreground">
            No analysis flags were raised for this device.
          </p>
        </Panel>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {report.flags.map((flag, index) => {
            const records = list(flag.record_ids).filter(
              (id) => typeof id === "string" && id.length > 0,
            );
            return (
              <li
                key={`${text(flag.reason, "flag")}-${index}`}
                className="rounded-xl border-2 border-ai-border bg-ai p-4 shadow-card transition-shadow hover:shadow-raised"
              >
                <p className="label-caps flex items-center gap-1.5 text-brand-dark">
                  <AlertTriangle className="h-3.5 w-3.5 text-brand-accent" aria-hidden />
                  ⚠ Analysis Flag
                </p>
                <p className="mt-2 text-sm font-semibold leading-snug text-foreground">
                  {text(flag.reason, "Unspecified analysis flag")}
                </p>
                {text(flag.source) && (
                  <p className="mt-2 text-xs text-brand-dark">
                    Source: <span className="font-mono">{text(flag.source)}</span>
                  </p>
                )}
                {records.length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-ai-border pt-3">
                    <span className="text-xs text-brand-dark">Related records:</span>
                    {records.map((id) => (
                      <RecordId key={id} id={id} tone="red" />
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
