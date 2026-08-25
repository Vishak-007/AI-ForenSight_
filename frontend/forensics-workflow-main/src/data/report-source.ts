import type { ReportData } from "@/lib/report-types";
import { mockReport } from "./mock-report";

/**
 * Single integration point for the report dataset.
 *
 * To use the real file produced by the analysis module:
 *   1. Place `report_data.json` in this folder.
 *   2. `import realReport from "./report_data.json";`
 *   3. `export const reportData: ReportData = realReport as ReportData;`
 *
 * No UI component reads anything other than this export.
 */
export const reportData: ReportData = mockReport;
