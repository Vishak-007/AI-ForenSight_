/**
 * Forensics backend service abstraction.
 *
 * The real analysis pipeline (UFDR parsing, Whisper, YOLO, Tesseract, entity
 * extraction, correlation, report assembly) lives OUTSIDE the frontend.
 * This module is the only place that talks to it. For development it uses a
 * mock asynchronous implementation; to connect the real backend, replace the
 * bodies of the four exported functions with fetch() calls that return the
 * same shapes. No UI component imports anything else.
 */

import type { ReportData } from "@/lib/report-types";
import { mockReport } from "@/data/mock-report";

/* ------------------------------- contracts ------------------------------- */

export type StageState = "pending" | "processing" | "completed" | "failed";

export interface AnalysisStage {
  id: string;
  label: string;
  state: StageState;
}

export type AnalysisState = "idle" | "running" | "completed" | "failed";

export interface UploadResult {
  caseId: string;
  deviceId: string | null;
  fileName: string;
  fileSize: number;
  uploadedAt: string;
}

export interface AnalysisStatus {
  analysisId: string;
  state: AnalysisState;
  progress: number; // 0..100
  stages: AnalysisStage[];
  message: string;
  error?: string;
}

export class ForensicsApiError extends Error {}

export const STAGE_DEFS: { id: string; label: string }[] = [
  { id: "upload", label: "UFDR File Uploaded" },
  { id: "parse", label: "Parsing" },
  { id: "messages", label: "Message Extraction" },
  { id: "calls", label: "Call Extraction" },
  { id: "media", label: "Media Extraction" },
  { id: "whisper", label: "Audio Transcription — Whisper" },
  { id: "yolo", label: "Image Object Detection — YOLO" },
  { id: "ocr", label: "OCR — Tesseract" },
  { id: "entities", label: "Entity & Flag Analysis" },
  { id: "correlation", label: "Correlation" },
  { id: "assembly", label: "Report Data Assembly" },
  { id: "report", label: "Generating Report" },
];

export const UFDR_EXTENSION = ".ufdr";

export const isValidUfdrFile = (file: File): boolean =>
  file.name.trim().toLowerCase().endsWith(UFDR_EXTENSION) && file.size > 0;

export const formatFileSize = (bytes: number): string => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

/* ------------------------------ mock backend ----------------------------- */

const STAGE_MS = 1100;
const started = new Map<string, number>();

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

const makeCaseId = () => {
  const now = new Date();
  const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(
    now.getDate(),
  ).padStart(2, "0")}`;
  const rand = Math.floor(Math.random() * 9000 + 1000);
  return `CASE-${stamp}-${rand}`;
};

/** Upload the UFDR extraction file. Reports 0..100 upload progress. */
export async function uploadUFDR(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadResult> {
  if (!isValidUfdrFile(file)) {
    throw new ForensicsApiError("Please upload a valid UFDR file.");
  }
  for (let p = 0; p <= 100; p += 10) {
    onProgress?.(p);
    await wait(90);
  }
  return {
    caseId: makeCaseId(),
    deviceId: mockReport.device_id ?? null,
    fileName: file.name,
    fileSize: file.size,
    uploadedAt: new Date().toISOString(),
  };
}

/** Kick off the backend forensic analysis pipeline for an uploaded case. */
export async function startAnalysis(caseId: string): Promise<{ analysisId: string }> {
  if (!caseId) throw new ForensicsApiError("No case file is available for analysis.");
  await wait(400);
  const analysisId = `AN-${caseId}`;
  started.set(analysisId, Date.now());
  return { analysisId };
}

/** Poll the pipeline status. Safe to call repeatedly. */
export async function getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
  const startedAt = started.get(analysisId);
  if (!startedAt) {
    // The mock backend lost the job (e.g. page reload). Report it as complete
    // when a report can still be assembled, so the investigator is not blocked.
    started.set(analysisId, Date.now() - STAGE_MS * (STAGE_DEFS.length + 1));
    return getAnalysisStatus(analysisId);
  }
  const done = Math.floor((Date.now() - startedAt) / STAGE_MS);
  const stages: AnalysisStage[] = STAGE_DEFS.map((s, i) => ({
    ...s,
    state: i < done ? "completed" : i === done ? "processing" : "pending",
  }));
  const completed = done >= STAGE_DEFS.length;
  const progress = Math.min(100, Math.round((done / STAGE_DEFS.length) * 100));
  return {
    analysisId,
    state: completed ? "completed" : "running",
    progress: completed ? 100 : progress,
    stages,
    message: completed
      ? "Analysis complete."
      : `Analysis is running… ${stages.find((s) => s.state === "processing")?.label ?? ""}`.trim(),
  };
}

/** Fetch the assembled report_data.json for a completed analysis. */
export async function getReportData(caseId: string): Promise<ReportData> {
  if (!caseId) throw new ForensicsApiError("Report data is unavailable for this case.");
  await wait(350);
  return mockReport;
}
