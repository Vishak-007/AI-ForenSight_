import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import { generateReportPdf, pdfFileName } from "@/lib/generate-report-pdf";
import type { NormalizedReport } from "@/lib/report-types";
import type { UploadResult } from "@/services/forensics-api";

export function PDFGenerator({
  report,
  upload,
  analyst,
  investigationDate,
  completedAt,
  analysisComplete,
  compact,
}: {
  report: NormalizedReport;
  upload: UploadResult | null;
  analyst: string;
  investigationDate: string;
  completedAt: string | null;
  analysisComplete: boolean;
  compact?: boolean;
}) {
  const [generating, setGenerating] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const urlRef = useRef<string | null>(null);

  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  const generate = useCallback(async () => {
    if (!analysisComplete) {
      setError("Analysis is not complete. Run the forensic analysis before generating a report.");
      return;
    }
    setError(null);
    setGenerating(true);
    try {
      // yield a frame so the loading state paints before the synchronous build
      await new Promise((r) => setTimeout(r, 50));
      const blob = generateReportPdf(report, {
        upload,
        analyst,
        investigationDate,
        completedAt,
      });
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      const next = URL.createObjectURL(blob);
      urlRef.current = next;
      setUrl(next);
    } catch {
      setError("The PDF report could not be generated. Please try again.");
    } finally {
      setGenerating(false);
    }
  }, [analysisComplete, report, upload, analyst, investigationDate, completedAt]);

  return (
    <div className={compact ? "" : "rounded-xl border border-border bg-card p-4 shadow-card"}>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={generate}
          disabled={generating}
          className="focus-ring label-caps inline-flex items-center justify-center gap-2 rounded-lg bg-brand-deep px-4 py-3 text-primary-foreground shadow-red transition-colors hover:bg-brand-dark disabled:opacity-60"
        >
          {generating ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <FileText className="h-4 w-4" aria-hidden />
          )}
          {generating ? "Generating PDF…" : "Generate PDF Report"}
        </button>

        {url && (
          <a
            href={url}
            download={pdfFileName(upload?.caseId ?? "case")}
            className="focus-ring label-caps inline-flex items-center justify-center gap-2 rounded-lg border border-brand-deep px-4 py-3 text-brand-deep transition-colors hover:bg-ai"
          >
            <Download className="h-4 w-4" aria-hidden />
            Download PDF Report
          </a>
        )}
      </div>

      {error && (
        <p
          role="alert"
          className="mt-3 rounded-lg border border-ai-border bg-ai px-3 py-2 text-sm font-semibold text-brand-dark"
        >
          {error}
        </p>
      )}
      {!compact && (
        <p className="mt-3 text-xs text-muted-foreground">
          The PDF is produced from the analysed report data with AI-generated content clearly
          marked.
        </p>
      )}
    </div>
  );
}
