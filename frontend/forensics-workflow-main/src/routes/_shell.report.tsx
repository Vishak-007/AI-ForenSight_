import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, LayoutDashboard, ListTree, Users, ShieldAlert, Images } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ReportPreview } from "@/components/forensics/ReportPreview";
import { PDFGenerator } from "@/components/forensics/PDFGenerator";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { useInvestigation } from "@/lib/investigation";
import { useAuth } from "@/lib/auth";
import { useReport } from "@/lib/use-report";
import { formatTimestamp } from "@/lib/report-types";

const title = "Final Investigation Report — Evidence Examiner Desk";
const description =
  "Final digital forensics investigation report: case overview, AI summary, evidence statistics, entities, analysis findings and the full evidence timeline, exportable as PDF.";

export const Route = createFileRoute("/_shell/report")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: ReportPage,
});

const QUICK_LINKS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/timeline", label: "Timeline", icon: ListTree },
  { to: "/entities", label: "Entities", icon: Users },
  { to: "/flags", label: "Flags", icon: ShieldAlert },
  { to: "/media", label: "Media", icon: Images },
] as const;

function ReportPage() {
  const { upload, analysisState, reportData, startedAt, completedAt } = useInvestigation();
  const { user } = useAuth();
  const report = useReport();

  const analysisComplete = analysisState === "completed" && reportData !== null;
  const hasData = report.timeline.length > 0 || report.entities.length > 0;

  return (
    <>
      <PageHeader
        title="Final Report"
        description="Complete investigation report preview and PDF export."
        actions={
          <Link
            to="/dashboard"
            className="focus-ring inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm font-semibold text-foreground hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to Investigation
          </Link>
        }
      />

      <div className="mb-5 flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
        <PDFGenerator
          compact
          report={report}
          upload={upload}
          analyst={user?.name ?? "Investigator"}
          investigationDate={startedAt ? formatTimestamp(startedAt) : "Not recorded"}
          completedAt={completedAt ? formatTimestamp(completedAt) : null}
          analysisComplete={analysisComplete}
        />
        <nav aria-label="Investigation sections" className="flex flex-wrap gap-2">
          {QUICK_LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="focus-ring inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-muted-foreground hover:bg-muted hover:text-brand-dark"
            >
              <link.icon className="h-3.5 w-3.5" aria-hidden />
              {link.label}
            </Link>
          ))}
        </nav>
      </div>

      {!analysisComplete && (
        <Panel className="mb-5">
          <SectionLabel>Analysis not complete</SectionLabel>
          <div className="p-4">
            <p className="text-sm text-muted-foreground">
              {upload
                ? "Run the forensic analysis for this case before exporting the official PDF report. The preview below uses the currently loaded report data."
                : "No UFDR case file has been analysed in this session. Start a new investigation to generate an official report; the preview below uses the currently loaded report data."}
            </p>
            <Link
              to="/upload"
              className="focus-ring label-caps mt-3 inline-flex items-center rounded-lg bg-brand-deep px-4 py-2.5 text-primary-foreground shadow-red hover:bg-brand-dark"
            >
              Go to UFDR Upload
            </Link>
          </div>
        </Panel>
      )}

      {hasData ? (
        <ReportPreview
          report={report}
          upload={upload}
          analyst={user?.name ?? "Investigator"}
          investigationDate={startedAt ? formatTimestamp(startedAt) : "Not recorded"}
          completedAt={completedAt ? formatTimestamp(completedAt) : null}
        />
      ) : (
        <Panel>
          <SectionLabel>Missing report data</SectionLabel>
          <p className="p-4 text-sm text-muted-foreground">
            No report data is available. Complete a forensic analysis to populate this report.
          </p>
        </Panel>
      )}
    </>
  );
}
