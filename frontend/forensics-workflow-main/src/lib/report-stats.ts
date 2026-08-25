import type { NormalizedReport } from "@/lib/report-types";
import { list, text } from "@/lib/report-types";

export interface EvidenceStats {
  messages: number;
  calls: number;
  audio: number;
  images: number;
  ocr: number;
  objects: number;
  entities: number;
  flags: number;
  records: number;
}

export function evidenceStats(report: NormalizedReport): EvidenceStats {
  const byKind = (kind: string) => report.timeline.filter((r) => r.kind === kind).length;
  return {
    messages: byKind("message"),
    calls: byKind("call"),
    audio: byKind("audio"),
    images: byKind("image"),
    ocr: report.timeline.filter((r) => text(r.ocr_text).length > 0).length,
    objects: report.timeline.reduce((n, r) => n + list(r.detected_objects).length, 0),
    entities: report.entities.length,
    flags: report.flags.length,
    records: report.timeline.length,
  };
}
