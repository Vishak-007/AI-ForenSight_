import { Sparkles, TriangleAlert, Image as ImageIcon } from "lucide-react";
import { ReportSection, AiNotice } from "@/components/forensics/ReportSection";
import { RecordId, KindBadge } from "@/components/forensics/primitives";
import { StatCard } from "@/components/forensics/StatCard";
import { evidenceStats } from "@/lib/report-stats";
import { confidencePercent, formatTimestamp, list, text } from "@/lib/report-types";
import type { NormalizedReport } from "@/lib/report-types";
import { formatFileSize } from "@/services/forensics-api";
import type { UploadResult } from "@/services/forensics-api";

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="label-caps text-muted-foreground">{label}</p>
      <p className="mt-0.5 break-words font-mono text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

export function ReportPreview({
  report,
  upload,
  analyst,
  investigationDate,
  completedAt,
}: {
  report: NormalizedReport;
  upload: UploadResult | null;
  analyst: string;
  investigationDate: string;
  completedAt: string | null;
}) {
  const stats = evidenceStats(report);
  const caseId = upload?.caseId ?? "UNASSIGNED";

  return (
    <article>
      <header className="overflow-hidden rounded-xl border border-border shadow-card">
        <div className="bg-brand-deep px-4 py-6 sm:px-6">
          <h1 className="text-lg font-bold tracking-tight text-primary-foreground sm:text-2xl">
            DIGITAL FORENSICS INVESTIGATION REPORT
          </h1>
          <p className="mt-1 text-sm text-primary-foreground/85">
            Evidence Examiner Desk — Official Case Report
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4 bg-card p-4 sm:grid-cols-3 sm:p-6 lg:grid-cols-6">
          <Meta label="Case ID" value={caseId} />
          <Meta label="Device ID" value={report.device_id} />
          <Meta label="Investigation date" value={investigationDate} />
          <Meta label="Report generated" value={new Date().toLocaleString()} />
          <Meta label="Analyst" value={analyst} />
          <Meta label="Analysis status" value={completedAt ? "Complete" : "Incomplete"} />
        </div>
      </header>

      <ReportSection index={1} title="Case Overview">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Meta label="Case ID" value={caseId} />
          <Meta label="Device ID" value={report.device_id} />
          <Meta label="UFDR file" value={upload?.fileName ?? "Not recorded"} />
          <Meta
            label="File size"
            value={upload ? formatFileSize(upload.fileSize) : "Not recorded"}
          />
          <Meta label="Evidence records" value={String(stats.records)} />
          <Meta
            label="Analysis completion"
            value={completedAt ? `Completed ${completedAt}` : "Not completed"}
          />
        </div>
      </ReportSection>

      <ReportSection index={2} title="Executive / AI Summary">
        <AiNotice>
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          ✦ AI-generated summary
        </AiNotice>
        <div className="rounded-lg border border-ai-border bg-ai p-4">
          <p className="text-sm leading-relaxed text-foreground">
            {report.overall_summary || "No summary was produced by the analysis pipeline."}
          </p>
          <p className="label-caps mt-3 text-brand-dark">
            AI-generated analysis. Verify against source evidence.
          </p>
        </div>
      </ReportSection>

      <ReportSection index={3} title="Evidence Statistics">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard icon={<span />} label="Messages" value={String(stats.messages)} />
          <StatCard icon={<span />} label="Calls" value={String(stats.calls)} />
          <StatCard icon={<span />} label="Audio" value={String(stats.audio)} />
          <StatCard icon={<span />} label="Images" value={String(stats.images)} />
          <StatCard icon={<span />} label="OCR results" value={String(stats.ocr)} />
          <StatCard icon={<span />} label="Detected objects" value={String(stats.objects)} />
          <StatCard icon={<span />} label="Entities" value={String(stats.entities)} />
          <StatCard icon={<span />} label="Flags" value={String(stats.flags)} />
        </div>
      </ReportSection>

      <ReportSection index={4} title="Entities">
        {report.entities.length === 0 ? (
          <p className="text-sm text-muted-foreground">No entities were extracted.</p>
        ) : (
          <ul className="divide-y divide-border">
            {report.entities.map((e, i) => (
              <li key={`${text(e.name, "entity")}-${i}`} className="py-3 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-bold text-foreground">
                    {text(e.name, "Unnamed entity")}
                  </span>
                  <KindBadge kind={text(e.type, "unknown")} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Known contact: {text(e.known_contact, "Not identified")}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {list(e.record_ids).map((id) => (
                    <RecordId key={id} id={id} />
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </ReportSection>

      <ReportSection index={5} title="Flags / Analysis Findings">
        {report.flags.length === 0 ? (
          <p className="text-sm text-muted-foreground">No analysis findings were derived.</p>
        ) : (
          <ul className="space-y-3">
            {report.flags.map((f, i) => (
              <li key={i} className="rounded-lg border border-ai-border bg-ai p-4">
                <p className="label-caps flex items-center gap-2 text-brand-dark">
                  <TriangleAlert className="h-3.5 w-3.5" aria-hidden />⚠ Analysis / derived finding
                </p>
                <p className="mt-2 text-sm font-semibold text-foreground">
                  {text(f.reason, "Unspecified finding")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Source: {text(f.source, "unknown")}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {list(f.record_ids).map((id) => (
                    <RecordId key={id} id={id} tone="red" />
                  ))}
                </div>
                <p className="mt-2 text-xs text-brand-dark">
                  Derived by analysis — not a confirmed fact.
                </p>
              </li>
            ))}
          </ul>
        )}
      </ReportSection>

      <ReportSection index={6} title="Evidence Timeline">
        {report.timeline.length === 0 ? (
          <p className="text-sm text-muted-foreground">No timeline records available.</p>
        ) : (
          <ol className="space-y-4">
            {report.timeline.map((r) => (
              <li key={r.id} className="rounded-lg border border-border bg-background p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <RecordId id={r.id} />
                  <KindBadge kind={String(r.kind)} />
                  <span className="font-mono text-xs text-muted-foreground">
                    {formatTimestamp(r.timestamp)}
                  </span>
                </div>
                {text(r.headline) && (
                  <p className="mt-2 text-sm font-semibold text-foreground">{text(r.headline)}</p>
                )}
                {text(r.detail) && (
                  <p className="mt-1 text-sm text-muted-foreground">{text(r.detail)}</p>
                )}
                {text(r.transcript) && (
                  <p className="mt-2 rounded-md border border-border bg-card p-3 text-sm text-foreground">
                    <span className="label-caps block text-muted-foreground">Transcript</span>
                    {text(r.transcript)}
                  </p>
                )}
                {r.kind === "image" && text(r.media_uri) && (
                  <div className="mt-3 flex flex-wrap items-start gap-3">
                    <img
                      src={text(r.media_uri)}
                      alt={`Evidence image ${r.id}`}
                      loading="lazy"
                      className="h-24 w-32 rounded-md border border-border object-cover"
                    />
                    <span className="label-caps flex items-center gap-1.5 text-muted-foreground">
                      <ImageIcon className="h-3.5 w-3.5" aria-hidden />
                      Media thumbnail
                    </span>
                  </div>
                )}
                {text(r.ocr_text) && (
                  <p className="mt-2 rounded-md border border-border bg-card p-3 text-sm text-foreground">
                    <span className="label-caps block text-muted-foreground">OCR text</span>
                    {text(r.ocr_text)}
                  </p>
                )}
                {list(r.detected_objects).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {list(r.detected_objects).map((o, i) => {
                      const pct = confidencePercent(o.confidence);
                      return (
                        <span
                          key={`${text(o.label, "object")}-${i}`}
                          className="inline-flex items-center rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
                        >
                          {text(o.label, "object")}
                          {pct ? ` · ${pct}` : ""}
                        </span>
                      );
                    })}
                  </div>
                )}
                {text(r.caption) && (
                  <div className="mt-2 rounded-md border border-ai-border bg-ai p-3">
                    <p className="label-caps text-brand-dark">✦ AI caption — unverified</p>
                    <p className="mt-1 text-sm text-foreground">{text(r.caption)}</p>
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </ReportSection>
    </article>
  );
}
