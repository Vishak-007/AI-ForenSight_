import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Loader2, CheckCircle2, RotateCcw } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { UploadDropzone } from "@/components/forensics/UploadDropzone";
import { CaseOverview } from "@/components/forensics/CaseOverview";
import { AnalysisProgress, AnalysisStatusBar } from "@/components/forensics/AnalysisProgress";
import { StatCard } from "@/components/forensics/StatCard";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { useInvestigation } from "@/lib/investigation";
import { useReport } from "@/lib/use-report";
import { evidenceStats } from "@/lib/report-stats";

const title = "New Investigation — UFDR Upload & Analysis";
const description =
  "Upload a UFDR extraction file and run the forensic analysis pipeline: parsing, transcription, object detection, OCR, entity analysis and report assembly.";

export const Route = createFileRoute("/_shell/upload")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: UploadPage,
});

function UploadPage() {
  const [caseNameInput, setCaseNameInput] = useState("Step 5C Test Case");
  const {
    upload,
    uploading,
    uploadProgress,
    analysisState,
    progress,
    stages,
    statusMessage,
    error,
    uploadFile,
    clearFile,
    beginAnalysis,
  } = useInvestigation();
  const report = useReport();
  const stats = evidenceStats(report);

  const running = analysisState === "running";
  const complete = analysisState === "completed";

  return (
    <>
      <PageHeader
        title="New Investigation"
        description="Upload a UFDR extraction file to begin forensic analysis."
      />

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-ai-border bg-ai px-4 py-3 text-sm font-semibold text-brand-dark"
        >
          {error}
        </p>
      )}

      {!upload && (
        <Panel>
          <SectionLabel>Upload UFDR Case File</SectionLabel>
          <div className="p-4">
            <p className="mb-4 text-sm text-muted-foreground">
              Upload a UFDR extraction file to begin forensic analysis. The file is processed by the
              forensic analysis service — no evidence is analysed in the browser.
            </p>

            <div className="mb-4">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-foreground">
                Forensic Case Name
              </label>
              <input
                type="text"
                value={caseNameInput}
                onChange={(e) => setCaseNameInput(e.target.value)}
                placeholder="Enter forensic case name..."
                disabled={uploading}
                className="w-full rounded-lg border border-border bg-card px-3.5 py-2.5 text-sm text-foreground focus:border-brand-accent focus:outline-none disabled:opacity-50"
              />
            </div>

            <UploadDropzone onFile={(f) => uploadFile(f, caseNameInput)} disabled={uploading} />

            {uploading && (
              <div className="mt-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                  <Loader2 className="h-4 w-4 animate-spin text-brand-deep" aria-hidden />
                  Uploading… {uploadProgress}%
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-brand-deep transition-all"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </Panel>
      )}

      {upload && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <CaseOverview
            upload={upload}
            analysisState={analysisState}
            uploadProgress={uploadProgress}
            busy={running}
            onRemove={running ? undefined : clearFile}
            onStart={analysisState === "idle" || analysisState === "failed" ? beginAnalysis : undefined}
          />

          <div className="space-y-5">
            {analysisState !== "idle" && (
              <>
                <AnalysisStatusBar
                  progress={progress}
                  state={analysisState}
                  message={statusMessage}
                />
                <AnalysisProgress stages={stages} />
              </>
            )}
            {analysisState === "idle" && (
              <Panel>
                <SectionLabel>Analysis Pipeline</SectionLabel>
                <div className="p-4 text-sm text-muted-foreground">
                  Analysis has not started. Click{" "}
                  <span className="font-semibold text-foreground">Start Forensic Analysis</span> to
                  run parsing, message and call extraction, Whisper transcription, YOLO object
                  detection, Tesseract OCR, entity and flag analysis, correlation and report
                  assembly.
                </div>
              </Panel>
            )}
          </div>
        </div>
      )}

      {complete && (
        <section className="mt-5">
          <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-4 shadow-card">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden />
            <h2 className="label-caps text-foreground">Analysis Complete</h2>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard icon={<span />} label="Messages" value={String(stats.messages)} />
            <StatCard icon={<span />} label="Calls" value={String(stats.calls)} />
            <StatCard icon={<span />} label="Images" value={String(stats.images)} />
            <StatCard icon={<span />} label="Audio files" value={String(stats.audio)} />
            <StatCard icon={<span />} label="OCR results" value={String(stats.ocr)} />
            <StatCard icon={<span />} label="Detected objects" value={String(stats.objects)} />
            <StatCard icon={<span />} label="Entities" value={String(stats.entities)} />
            <StatCard icon={<span />} label="Flags" value={String(stats.flags)} />
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to="/dashboard"
              className="focus-ring label-caps inline-flex items-center justify-center rounded-lg bg-brand-deep px-4 py-3 text-primary-foreground shadow-red hover:bg-brand-dark"
            >
              View Investigation
            </Link>
            <Link
              to="/timeline"
              className="focus-ring label-caps inline-flex items-center justify-center rounded-lg border border-border px-4 py-3 text-foreground hover:bg-muted"
            >
              View Timeline
            </Link>
            <Link
              to="/report"
              className="focus-ring label-caps inline-flex items-center justify-center rounded-lg border border-brand-deep px-4 py-3 text-brand-deep hover:bg-ai"
            >
              Generate Final Report
            </Link>
            <button
              type="button"
              onClick={clearFile}
              className="focus-ring inline-flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold text-muted-foreground hover:bg-muted"
            >
              <RotateCcw className="h-4 w-4" aria-hidden />
              Start a new investigation
            </button>
          </div>
        </section>
      )}
    </>
  );
}
