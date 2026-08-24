/**
 * Data contract for report_data.json produced by the analysis module.
 * The UI is built strictly against these types — swapping mock data for the
 * real JSON requires no UI changes.
 */

export type RecordKind = "message" | "call" | "audio" | "image";

export interface DetectedObject {
  label?: string | null;
  confidence?: number | null;
}

export interface TimelineRecord {
  id: string;
  kind: RecordKind | string;
  timestamp?: string | null;
  headline?: string | null;
  detail?: string | null;
  transcript?: string | null;
  ocr_text?: string | null;
  caption?: string | null;
  caption_status?: string | null;
  media_uri?: string | null;
  detected_objects?: DetectedObject[] | null;
}

export interface Entity {
  name?: string | null;
  type?: string | null;
  record_ids?: string[] | null;
  known_contact?: string | null;
}

export interface Flag {
  reason?: string | null;
  record_ids?: string[] | null;
  source?: string | null;
}

export interface ReportData {
  device_id?: string | null;
  overall_summary?: string | null;
  entities?: Entity[] | null;
  flags?: Flag[] | null;
  timeline?: TimelineRecord[] | null;
}

/* ---------- safe accessors: never render null / undefined / NaN ---------- */

export const text = (value: unknown, fallback = ""): string =>
  typeof value === "string" && value.trim().length > 0 ? value : fallback;

export const list = <T>(value: T[] | null | undefined): T[] =>
  Array.isArray(value) ? value : [];

export const confidencePercent = (value?: number | null): string | null => {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  const pct = value <= 1 ? value * 100 : value;
  return `${Math.round(pct)}%`;
};

export const formatTimestamp = (value?: string | null): string => {
  const raw = text(value);
  if (!raw) return "Unknown time";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const timestampValue = (value?: string | null): number => {
  const date = new Date(text(value));
  return Number.isNaN(date.getTime()) ? Number.MAX_SAFE_INTEGER : date.getTime();
};

export interface NormalizedReport {
  device_id: string;
  overall_summary: string;
  entities: Entity[];
  flags: Flag[];
  timeline: TimelineRecord[];
}

export const normalizeReport = (data: ReportData): NormalizedReport => ({
  device_id: text(data.device_id, "UNKNOWN"),
  overall_summary: text(data.overall_summary),
  entities: list(data.entities),
  flags: list(data.flags),
  timeline: list(data.timeline)
    .filter((r) => r && typeof r.id === "string")
    .slice()
    .sort((a, b) => timestampValue(a.timestamp) - timestampValue(b.timestamp)),
});
