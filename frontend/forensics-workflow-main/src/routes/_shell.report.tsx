import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, LayoutDashboard, ListTree, Users, ShieldAlert, Images, Loader2, AlertTriangle, FolderGit2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ReportPreview } from "@/components/forensics/ReportPreview";
import { PDFGenerator } from "@/components/forensics/PDFGenerator";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { useInvestigation } from "@/lib/investigation";
import { useAuth } from "@/lib/auth";
import { formatTimestamp, normalizeReport, type ReportData } from "@/lib/report-types";
import { getReportData, type UploadResult } from "@/services/forensics-api";

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
  const { activeCaseId, upload, startedAt, completedAt } = useInvestigation();
  const { user } = useAuth();

  const [rawReportData, setRawReportData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeCaseId === null) return;
    let mounted = true;
    setLoading(true);
    setError(null);

    getReportData(activeCaseId)
      .then((data) => {
        if (mounted) {
          setRawReportData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load report data.");
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [activeCaseId]);

  const report = useMemo(() => {
    if (!rawReportData) return null;
    return normalizeReport(rawReportData);
  }, [rawReportData]);

  const caseUpload: UploadResult = useMemo(() => {
    return {
      caseId: `CASE-${activeCaseId ?? 1}`,
      jobId: `JOB-${activeCaseId ?? 1}`,
      caseName: upload?.caseName || `Forensic Case #${activeCaseId ?? 1}`,
      deviceId: report?.device_id || "DEV001",
      fileName: upload?.fileName || "sample_ufdr/report.xml",
      fileSize: upload?.fileSize || 1048576,
      uploadedAt: upload?.uploadedAt || new Date().toISOString(),
    };
  }, [activeCaseId, report, upload]);

  const hasData = report !== null && (report.timeline.length > 0 || report.entities.length > 0);

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
            Back to Dashboard
          </Link>
        }
      />

      {/* Active Case Header Banner */}
      <div className="mb-4">
        <Panel>
          <SectionLabel
            icon={<FolderGit2 className="h-4 w-4 text-brand-deep" aria-hidden />}
            right={
              <span className="text-xs font-medium text-muted-foreground">
                Case #{activeCaseId ?? "-"} Active
              </span>
            }
          >
            Active Case #{activeCaseId ?? "-"} Final Report ({report ? report.timeline.length : 0} Timeline Records)
          </SectionLabel>

          {loading && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Assembling real report dataset from PostgreSQL...
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 border-l-4 border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </Panel>
      </div>

      {report && (
        <div className="mb-5 flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-card sm:flex-row sm:items-center sm:justify-between">
          <PDFGenerator
            compact
            report={report}
            upload={caseUpload}
            analyst={user?.name ?? "Lead Investigator"}
            investigationDate={startedAt ? formatTimestamp(startedAt) : new Date().toLocaleDateString()}
            completedAt={completedAt ? formatTimestamp(completedAt) : new Date().toLocaleDateString()}
            analysisComplete={true}
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
      )}

      {!loading && !error && hasData && report && (
        <ReportPreview
          report={report}
          upload={caseUpload}
          analyst={user?.name ?? "Lead Investigator"}
          investigationDate={startedAt ? formatTimestamp(startedAt) : new Date().toLocaleDateString()}
          completedAt={completedAt ? formatTimestamp(completedAt) : new Date().toLocaleDateString()}
        />
      )}

      {!loading && !error && !hasData && (
        <Panel>
          <SectionLabel>Missing report data</SectionLabel>
          <p className="p-4 text-sm text-muted-foreground">
            No report data is available for Case #{activeCaseId}.
          </p>
        </Panel>
      )}
    </>
  );
}

