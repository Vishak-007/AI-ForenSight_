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

import type { Entity, Flag, ReportData, TimelineRecord } from "@/lib/report-types";

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
  jobId: string;
  caseName: string;
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
  /** Postgres cases.id the pipeline imported this case as, once known. */
  caseId: number | null;
}

export class ForensicsApiError extends Error {}

export interface CaseRecord {
  id: number;
  case_name: string;
  source_file: string | null;
  created_at: string;
}

export interface DeviceRecord {
  id: number;
  case_id: number;
  device_id: string;
  imei: string | null;
  extraction_date: string | null;
}

export interface ContactRecord {
  id: number;
  case_id: number;
  contact_id: string;
  name: string | null;
  phone: string | null;
}

export interface MessageRecord {
  id: number;
  case_id: number;
  message_id: string;
  sender: string | null;
  receiver: string | null;
  timestamp: string | null;
  text: string | null;
}

export interface CallRecord {
  id: number;
  case_id: number;
  call_id: string;
  caller: string | null;
  callee: string | null;
  timestamp: string | null;
  duration_seconds: number | null;
  type: string | null;
}

export interface MediaRecord {
  id: number;
  case_id: number;
  media_id: string;
  type: string;
  timestamp: string | null;
  filename: string;
  storage_path: string;
  sha256: string | null;
  file_size_bytes: number | null;
  associated_message_id: string | null;
  associated_call_id: string | null;
  status: string | null;
}

export interface OcrResultRecord {
  id: number;
  media_id: number;
  text: string;
}

export interface TranscriptionRecord {
  id: number;
  media_id: number;
  text: string;
  language: string | null;
}

export interface ImageAnalysisRecord {
  id: number;
  media_id: number;
  width: number | null;
  height: number | null;
  format: string | null;
  context: string | null;
  face_count: number | null;
}

export interface ImageTagRecord {
  id: number;
  media_id: number;
  tag: string;
  confidence: number;
}



const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function getCases(): Promise<CaseRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cases`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch cases (HTTP ${response.status})`);
    }

    const data = await response.json();
    if (!Array.isArray(data)) {
      throw new ForensicsApiError("Invalid cases response format received from backend.");
    }

    return data;
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to forensic backend database.");
  }
}

export async function getDevices(caseId: number): Promise<DeviceRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/devices?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch devices for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to devices endpoint.");
  }
}

export async function getContacts(caseId: number): Promise<ContactRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/contacts?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch contacts for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to contacts endpoint.");
  }
}

export async function getMessages(caseId: number): Promise<MessageRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/messages?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch messages for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to messages endpoint.");
  }
}

export async function getCalls(caseId: number): Promise<CallRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/calls?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch calls for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to calls endpoint.");
  }
}

export async function getMedia(caseId: number): Promise<MediaRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/media?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch media records for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to media endpoint.");
  }
}

export async function getOcrResults(caseId: number): Promise<OcrResultRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/ocr-results?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch OCR results for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to OCR results endpoint.");
  }
}

export async function getTranscriptions(caseId: number): Promise<TranscriptionRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/transcriptions?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch transcriptions for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to transcriptions endpoint.");
  }
}

export async function getImageAnalysis(caseId: number): Promise<ImageAnalysisRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/image-analysis?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch image analysis for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to image analysis endpoint.");
  }
}

export async function getImageTags(caseId: number): Promise<ImageTagRecord[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/image-tags?case_id=${caseId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError(`Failed to fetch image tags for case #${caseId}`);
    }

    const data = await response.json();
    return Array.isArray(data) ? data : [];
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to image tags endpoint.");
  }
}




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

export const UFDR_EXTENSIONS = [".ufdr", ".zip"];

export const isValidUfdrFile = (file: File): boolean => {
  if (!file || file.size <= 0) return false;
  const name = file.name.trim().toLowerCase();
  return UFDR_EXTENSIONS.some((ext) => name.endsWith(ext));
};

export const formatFileSize = (bytes: number): string => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

/** Upload the UFDR archive file to the real backend. */
export async function uploadUFDR(
  file: File,
  caseName: string = "Sample Case",
  onProgress?: (percent: number) => void,
): Promise<UploadResult> {
  if (!isValidUfdrFile(file)) {
    throw new ForensicsApiError("Please upload a valid UFDR archive (.zip or .ufdr).");
  }

  const formData = new FormData();
  formData.append("case_name", caseName.trim() || file.name.replace(/\.[^/.]+$/, ""));
  formData.append("file", file);

  onProgress?.(30);

  try {
    const response = await fetch(`${API_BASE_URL}/api/cases/upload`, {
      method: "POST",
      body: formData,
    });

    onProgress?.(80);

    if (!response.ok) {
      let detail = `Upload rejected (HTTP ${response.status})`;
      try {
        const jsonErr = await response.json();
        if (jsonErr.detail) {
          detail = typeof jsonErr.detail === "string" ? jsonErr.detail : JSON.stringify(jsonErr.detail);
        }
      } catch {}
      throw new ForensicsApiError(detail);
    }

    const data = await response.json();
    onProgress?.(100);

    return {
      caseId: data.job_id,
      jobId: data.job_id,
      caseName: data.case_name || caseName,
      // Not known until the background pipeline finishes and reports the
      // Postgres case id (see getAnalysisStatus's caseId) -- report-types'
      // normalizeReport falls back to the real device_id once that lands.
      deviceId: null,
      fileName: file.name,
      fileSize: file.size,
      uploadedAt: new Date().toISOString(),
    };
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to backend upload endpoint.");
  }
}

/** Kick off the backend forensic analysis status tracking for an uploaded case job. */
export async function startAnalysis(jobId: string): Promise<{ analysisId: string }> {
  if (!jobId) throw new ForensicsApiError("No upload job ID available for analysis.");
  return { analysisId: jobId };
}

/** Poll real backend status for a background extraction job. */
export async function getAnalysisStatus(jobId: string): Promise<AnalysisStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cases/upload/status/${jobId}`, {
      method: "GET",
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError("Failed to fetch extraction status from backend.");
    }

    const data = await response.json();
    const backendStatus: "processing" | "completed" | "failed" = data.status || "processing";

    let state: AnalysisState = "running";
    let progress = 50;

    if (backendStatus === "completed") {
      state = "completed";
      progress = 100;
    } else if (backendStatus === "failed") {
      state = "failed";
      progress = 0;
    }

    const stages: AnalysisStage[] = STAGE_DEFS.map((s, i) => {
      if (backendStatus === "completed") {
        return { ...s, state: "completed" };
      }
      if (backendStatus === "failed") {
        return { ...s, state: i === 0 ? "completed" : "failed" };
      }
      return {
        ...s,
        state: i < 5 ? "completed" : i === 5 ? "processing" : "pending",
      };
    });

    return {
      analysisId: jobId,
      state,
      progress,
      stages,
      message:
        backendStatus === "completed"
          ? "Analysis complete."
          : backendStatus === "failed"
          ? (data.error_message || "Forensic pipeline processing failed.")
          : "Processing UFDR extraction pipeline in background...",
      error: backendStatus === "failed" ? (data.error_message || "Forensic pipeline processing failed.") : undefined,
      caseId: typeof data.case_id === "number" ? data.case_id : null,
    };
  } catch (error) {
    if (error instanceof ForensicsApiError) {
      throw error;
    }
    throw new ForensicsApiError("Unable to connect to status endpoint.");
  }
}


import { timestampValue } from "@/lib/report-types";

/** Fetch real assembled report data for a selected case from PostgreSQL endpoints. */
export async function getReportData(caseId: string | number): Promise<ReportData> {
  const numericId = typeof caseId === "number" ? caseId : parseInt(caseId, 10);
  const targetId = Number.isNaN(numericId) ? 1 : numericId;

  try {
    const [
      cases,
      devices,
      contacts,
      messages,
      calls,
      media,
      ocrResults,
      transcriptions,
      imageAnalysis,
      imageTags,
    ] = await Promise.all([
      getCases(),
      getDevices(targetId),
      getContacts(targetId),
      getMessages(targetId),
      getCalls(targetId),
      getMedia(targetId),
      getOcrResults(targetId),
      getTranscriptions(targetId),
      getImageAnalysis(targetId),
      getImageTags(targetId),
    ]);

    const targetCase = cases.find((c) => c.id === targetId) || cases[0];
    const deviceId = devices.length > 0 ? devices[0].device_id : "DEV001";
    const caseName = targetCase ? targetCase.case_name : `Case #${targetId}`;

    const summary = `Digital Forensics Report for ${caseName} (Case #${targetId}). System processed ${devices.length} device(s), ${contacts.length} contact(s), ${messages.length} message(s), ${calls.length} call(s), ${media.length} media item(s), ${ocrResults.length} OCR result(s), ${transcriptions.length} transcript(s), ${imageAnalysis.length} image analysis record(s), and ${imageTags.length} object tag(s).`;

    const entities: Entity[] = contacts.map((c) => ({
      name: c.name || c.contact_id,
      type: "Contact Record",
      known_contact: c.phone || "No phone listed",
      record_ids: [c.contact_id],
    }));

    const flags: Flag[] = [];
    if (ocrResults.length > 0) {
      flags.push({
        reason: `OCR Text Extracted (${ocrResults.length} item${ocrResults.length > 1 ? "s" : ""})`,
        source: "Tesseract OCR Engine",
        record_ids: ocrResults.map((o) => `MED-${o.media_id}`),
      });
    }
    if (transcriptions.length > 0) {
      flags.push({
        reason: `Audio Transcripts Extracted (${transcriptions.length} file${transcriptions.length > 1 ? "s" : ""})`,
        source: "Whisper Audio Transcriber",
        record_ids: transcriptions.map((t) => `MED-${t.media_id}`),
      });
    }
    if (imageAnalysis.length > 0) {
      flags.push({
        reason: `AI Image Scene Classification (${imageAnalysis.length} image${imageAnalysis.length > 1 ? "s" : ""})`,
        source: "OpenCV / CLIP Scene Detector",
        record_ids: imageAnalysis.map((a) => `MED-${a.media_id}`),
      });
    }
    if (imageTags.length > 0) {
      flags.push({
        reason: `Object Detections Tagged (${imageTags.length} detection${imageTags.length > 1 ? "s" : ""})`,
        source: "YOLO Object Classifier",
        record_ids: imageTags.map((t) => `MED-${t.media_id}`),
      });
    }

    const msgEvents: TimelineRecord[] = messages.map((m) => ({
      id: m.message_id || `MSG-${m.id}`,
      kind: "message",
      timestamp: m.timestamp,
      headline: `${m.sender || "Unknown"} → ${m.receiver || "Unknown"}`,
      detail: m.text || "No text content",
    }));

    const callEvents: TimelineRecord[] = calls.map((c) => ({
      id: c.call_id || `CALL-${c.id}`,
      kind: "call",
      timestamp: c.timestamp,
      headline: `${c.type ? (c.type.charAt(0).toUpperCase() + c.type.slice(1)) : "Call"} ${c.caller || "Unknown"} → ${c.callee || "Unknown"}`,
      detail: `Duration: ${c.duration_seconds != null ? `${c.duration_seconds}s` : "Unknown"} · Type: ${c.type || "unknown"}`,
    }));

    const mediaEvents: TimelineRecord[] = media.map((m) => {
      const ocr = ocrResults.find((o) => o.media_id === m.id);
      const tr = transcriptions.find((t) => t.media_id === m.id);
      const ia = imageAnalysis.find((a) => a.media_id === m.id);
      const tags = imageTags.filter((t) => t.media_id === m.id);

      let kind = m.type ? m.type.toLowerCase() : "image";
      if (kind === "document") kind = "image";

      return {
        id: m.media_id || `MED-${m.id}`,
        kind: kind,
        timestamp: m.timestamp,
        headline: m.filename,
        detail: `${formatFileSize(m.file_size_bytes || 0)} · Status: ${m.status || "PARSED"}${
          m.sha256 ? ` · SHA256: ${m.sha256.slice(0, 16)}...` : ""
        }`,
        media_uri: null,
        ocr_text: ocr ? ocr.text : null,
        transcript: tr ? tr.text : null,
        caption: ia ? (ia.context || (ia.width && ia.height ? `${ia.width}x${ia.height} ${ia.format || ""}` : null)) : null,
        caption_status: ia ? "verified" : null,
        detected_objects: tags.map((t) => ({ label: t.tag, confidence: t.confidence })),
      };
    });

    const combinedTimeline = [...msgEvents, ...callEvents, ...mediaEvents];
    combinedTimeline.sort((a, b) => timestampValue(a.timestamp) - timestampValue(b.timestamp));

    return {
      device_id: deviceId,
      overall_summary: summary,
      entities: entities,
      flags: flags,
      timeline: combinedTimeline,
    };
  } catch (error) {
    if (error instanceof ForensicsApiError) throw error;
    throw new ForensicsApiError("Failed to fetch real report data from database.");
  }
}

/* --------------------------- Audit Logs Services --------------------------- */

export interface AuditLogRecord {
  id: number;
  case_id: number | null;
  user_id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, any> | string | null;
  ip_address: string | null;
  user_agent: string | null;
  timestamp: string;
  prev_log_hash: string;
  entry_hash: string;
}

export interface AuditVerificationResult {
  status: "verified" | "corrupted" | "valid";
  total_entries: number;
  message: string;
  corrupted_at_id?: number;
  reason?: string;
  expected_prev_hash?: string;
  found_prev_hash?: string;
}

export async function getAuditLogs(params?: {
  caseId?: number | null;
  userId?: string;
  action?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; logs: AuditLogRecord[] }> {
  try {
    const url = new URL(`${API_BASE_URL}/api/audit-logs`);
    if (params?.caseId != null) url.searchParams.append("case_id", String(params.caseId));
    if (params?.userId) url.searchParams.append("user_id", params.userId);
    if (params?.action) url.searchParams.append("action", params.action);
    if (params?.limit !== undefined) url.searchParams.append("limit", String(params.limit));
    if (params?.offset !== undefined) url.searchParams.append("offset", String(params.offset));

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError("Failed to fetch audit log history from server.");
    }

    const data = await response.json();
    return {
      total: data.total || 0,
      logs: Array.isArray(data.logs) ? data.logs : [],
    };
  } catch (error) {
    if (error instanceof ForensicsApiError) throw error;
    throw new ForensicsApiError("Unable to connect to audit logs endpoint.");
  }
}

export async function verifyAuditTrail(): Promise<AuditVerificationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/audit-logs/verify`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new ForensicsApiError("Audit trail cryptographic verification request failed.");
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ForensicsApiError) throw error;
    throw new ForensicsApiError("Unable to reach audit verification service.");
  }
}

