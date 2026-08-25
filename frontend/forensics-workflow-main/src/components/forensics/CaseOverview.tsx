import { FileArchive, HardDrive, Hash, Trash2, Play } from "lucide-react";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { formatFileSize } from "@/services/forensics-api";
import type { AnalysisState, UploadResult } from "@/services/forensics-api";

const ANALYSIS_LABEL: Record<AnalysisState, string> = {
  idle: "Not started",
  running: "In progress",
  completed: "Completed",
  failed: "Failed",
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,10rem)_minmax(0,1fr)] gap-2 border-b border-border px-4 py-3 last:border-b-0">
      <span className="label-caps text-muted-foreground">{label}</span>
      <span className="min-w-0 break-words font-mono text-sm font-semibold text-foreground">
        {value}
      </span>
    </div>
  );
}

export function CaseOverview({
  upload,
  analysisState,
  uploadProgress,
  onRemove,
  onStart,
  busy,
}: {
  upload: UploadResult;
  analysisState: AnalysisState;
  uploadProgress: number;
  onRemove?: (() => void) | undefined;
  onStart?: (() => void | Promise<void>) | undefined;
  busy?: boolean | undefined;
}) {
  return (
    <Panel>
      <SectionLabel icon={<FileArchive className="h-4 w-4 text-brand-deep" aria-hidden />}>
        Case Information
      </SectionLabel>
      <div>
        <Row label="File name" value={upload.fileName} />
        <Row label="File size" value={formatFileSize(upload.fileSize)} />
        <Row
          label="Upload status"
          value={uploadProgress >= 100 ? "Uploaded" : `Uploading ${uploadProgress}%`}
        />
        <Row label="Case ID" value={upload.caseId} />
        <Row label="Device ID" value={upload.deviceId ?? "Not available"} />
        <Row label="Analysis status" value={ANALYSIS_LABEL[analysisState]} />
      </div>

      {(onStart || onRemove) && (
        <div className="flex flex-col gap-2 border-t border-border p-4 sm:flex-row sm:items-center sm:justify-between">
          {onRemove && (
            <button
              type="button"
              onClick={onRemove}
              disabled={busy}
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm font-semibold text-muted-foreground transition-colors hover:bg-muted disabled:opacity-60"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
              Remove / reselect file
            </button>
          )}
          {onStart && (
            <button
              type="button"
              onClick={() => void onStart()}
              disabled={busy}
              className="focus-ring label-caps inline-flex items-center justify-center gap-2 rounded-lg bg-brand-deep px-4 py-3 text-primary-foreground shadow-red transition-colors hover:bg-brand-dark disabled:opacity-60"
            >
              <Play className="h-4 w-4" aria-hidden />
              Start Forensic Analysis
            </button>
          )}
        </div>
      )}
    </Panel>
  );
}

export function DeviceChip({ deviceId }: { deviceId: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-ai-border bg-ai px-3 py-1.5">
      <HardDrive className="h-4 w-4 text-brand-deep" aria-hidden />
      <span className="label-caps text-brand-dark">Device {deviceId}</span>
    </span>
  );
}

export function CaseChip({ caseId }: { caseId: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-3 py-1.5">
      <Hash className="h-4 w-4 text-brand-deep" aria-hidden />
      <span className="label-caps text-foreground">{caseId}</span>
    </span>
  );
}
