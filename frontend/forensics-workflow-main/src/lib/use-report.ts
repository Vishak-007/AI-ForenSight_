import { useMemo } from "react";
import { reportData as fallbackReport } from "@/data/report-source";
import { useInvestigationOptional } from "@/lib/investigation";
import type { NormalizedReport, TimelineRecord } from "@/lib/report-types";
import { list, normalizeReport, text } from "@/lib/report-types";

/** Single shared access point to the report dataset for every page. */
export function useReport(): NormalizedReport {
  // Prefer report_data.json produced by the current investigation; fall back to
  // the bundled dataset so every page still renders before an analysis is run.
  const investigation = useInvestigationOptional();
  const data = investigation?.reportData ?? fallbackReport;
  return useMemo(() => normalizeReport(data), [data]);
}

export const matchesQuery = (record: TimelineRecord, query: string): boolean => {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [record.id, record.headline, record.detail, record.transcript, record.ocr_text]
    .map((field) => text(field).toLowerCase())
    .join(" \u0000 ")
    .includes(q);
};

export const filterRecords = (
  records: TimelineRecord[],
  query: string,
  allowedIds: string[] | null,
): TimelineRecord[] => {
  const allowed = allowedIds ? new Set(allowedIds) : null;
  return records.filter(
    (record) => (!allowed || allowed.has(record.id)) && matchesQuery(record, query),
  );
};

export const entityRecordIds = (entity: { record_ids?: string[] | null } | undefined) =>
  entity ? list(entity.record_ids).filter((id) => typeof id === "string" && id.length > 0) : [];

export const recordsByIds = (records: TimelineRecord[], ids: string[]): TimelineRecord[] => {
  const set = new Set(ids);
  return records.filter((r) => set.has(r.id));
};
