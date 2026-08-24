import { jsPDF } from "jspdf";
import type { NormalizedReport } from "@/lib/report-types";
import { confidencePercent, formatTimestamp, list, text } from "@/lib/report-types";
import { evidenceStats } from "@/lib/report-stats";
import { formatFileSize } from "@/services/forensics-api";
import type { UploadResult } from "@/services/forensics-api";

export interface PdfMeta {
  upload: UploadResult | null;
  analyst: string;
  investigationDate: string;
  completedAt: string | null;
}

const RED: [number, number, number] = [185, 28, 28];
const DARK: [number, number, number] = [127, 29, 29];
const INK: [number, number, number] = [24, 24, 27];
const GREY: [number, number, number] = [100, 100, 106];
const AI_BG: [number, number, number] = [253, 237, 237];

const MARGIN = 48;

/** jsPDF core fonts are Latin-1 only: map common symbols to safe equivalents. */
const safe = (value: string): string =>
  value
    .replace(/[\u2192\u27a1]/g, "->")
    .replace(/[\u2190]/g, "<-")
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u2013\u2014]/g, "-")
    .replace(/[\u2026]/g, "...")
    .replace(/[\u2022]/g, "-")
    .replace(/[\u00d7]/g, "x")
    .replace(/[\u2726\u2727\u26a0\ufe0f]/g, "")
    // strip anything outside Latin-1 so no glyph renders as noise
    .replace(/[^\u0000-\u00ff]/g, "");

export function generateReportPdf(report: NormalizedReport, meta: PdfMeta): Blob {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  const CONTENT = W - MARGIN * 2;
  let y = MARGIN;
  let page = 1;

  const stats = evidenceStats(report);
  const caseId = meta.upload?.caseId ?? "UNASSIGNED";
  const generatedAt = new Date().toLocaleString();

  const footer = () => {
    doc.setDrawColor(...RED);
    doc.setLineWidth(1);
    doc.line(MARGIN, H - 44, W - MARGIN, H - 44);
    doc.setFont("helvetica", "normal").setFontSize(8).setTextColor(...GREY);
    doc.text(safe(`Case ${caseId}  -  Digital Forensics Investigation Report`), MARGIN, H - 30);
    doc.text(`Page ${page}`, W - MARGIN, H - 30, { align: "right" });
  };

  const newPage = () => {
    footer();
    doc.addPage();
    page += 1;
    y = MARGIN;
  };

  const need = (h: number) => {
    if (y + h > H - 64) newPage();
  };

  const heading = (n: number, title: string) => {
    need(46);
    y += 10;
    doc.setFillColor(...RED);
    doc.rect(MARGIN, y, CONTENT, 22, "F");
    doc.setFont("helvetica", "bold").setFontSize(11).setTextColor(255, 255, 255);
    doc.text(safe(`${n}.  ${title.toUpperCase()}`), MARGIN + 8, y + 15);
    y += 34;
  };

  const para = (
    value: string,
    opts: { bold?: boolean; size?: number; color?: [number, number, number]; indent?: number } = {},
  ) => {
    const size = opts.size ?? 10;
    const indent = opts.indent ?? 0;
    doc
      .setFont("helvetica", opts.bold ? "bold" : "normal")
      .setFontSize(size)
      .setTextColor(...(opts.color ?? INK));
    const lines = doc.splitTextToSize(safe(value), CONTENT - indent) as string[];
    lines.forEach((line) => {
      need(size + 4);
      doc.text(line, MARGIN + indent, y);
      y += size + 4;
    });
  };

  const aiBlock = (label: string, body: string) => {
    const size = 10;
    doc.setFont("helvetica", "normal").setFontSize(size);
    const lines = doc.splitTextToSize(safe(body), CONTENT - 24) as string[];
    const h = 26 + lines.length * (size + 4) + 10;
    need(h);
    doc.setFillColor(...AI_BG);
    doc.setDrawColor(...RED);
    doc.setLineWidth(1);
    doc.rect(MARGIN, y, CONTENT, h, "FD");
    doc.setFont("helvetica", "bold").setFontSize(8).setTextColor(...DARK);
    doc.text(safe(label).toUpperCase(), MARGIN + 12, y + 16);
    doc.setFont("helvetica", "normal").setFontSize(size).setTextColor(...INK);
    let ly = y + 32;
    lines.forEach((line) => {
      doc.text(line, MARGIN + 12, ly);
      ly += size + 4;
    });
    y += h + 10;
  };

  const kv = (label: string, value: string) => {
    need(16);
    doc.setFont("helvetica", "bold").setFontSize(9.5).setTextColor(...GREY);
    doc.text(safe(label), MARGIN, y);
    doc.setFont("helvetica", "normal").setTextColor(...INK);
    const lines = doc.splitTextToSize(safe(value), CONTENT - 150) as string[];
    lines.forEach((line, i) => {
      if (i > 0) need(14);
      doc.text(line, MARGIN + 150, y);
      if (i < lines.length - 1) y += 14;
    });
    y += 16;
  };

  const rule = () => {
    need(12);
    doc.setDrawColor(226, 226, 230);
    doc.setLineWidth(0.6);
    doc.line(MARGIN, y, W - MARGIN, y);
    y += 12;
  };

  /* ------------------------------ cover header ----------------------------- */
  doc.setFillColor(...RED);
  doc.rect(0, 0, W, 132, "F");
  doc.setFont("helvetica", "bold").setFontSize(20).setTextColor(255, 255, 255);
  doc.text("DIGITAL FORENSICS", MARGIN, 58);
  doc.text("INVESTIGATION REPORT", MARGIN, 84);
  doc.setFont("helvetica", "normal").setFontSize(10);
  doc.text("Evidence Examiner Desk  -  Official Case Report", MARGIN, 108);
  y = 168;

  kv("Case ID", caseId);
  kv("Device ID", report.device_id);
  kv("UFDR file", meta.upload ? meta.upload.fileName : "Not recorded");
  kv("File size", meta.upload ? formatFileSize(meta.upload.fileSize) : "Not recorded");
  kv("Investigation date", meta.investigationDate);
  kv("Report generated", generatedAt);
  kv("Analyst", meta.analyst);
  kv("Analysis status", meta.completedAt ? "Complete" : "Incomplete");
  rule();
  para(
    "This document contains recovered device evidence together with clearly labelled analysis-derived and AI-generated content. AI-generated text and derived findings are not confirmed facts and must be verified against the source evidence.",
    { size: 9, color: GREY },
  );

  /* 1. Case overview */
  heading(1, "Case Overview");
  kv("Case ID", caseId);
  kv("Device ID", report.device_id);
  kv("Evidence records", String(stats.records));
  kv("Analysis completion", meta.completedAt ? `Completed ${meta.completedAt}` : "Not completed");

  /* 2. Executive / AI summary */
  heading(2, "Executive / AI Summary");
  aiBlock(
    "AI-generated summary — AI-generated analysis. Verify against source evidence.",
    report.overall_summary || "No summary was produced by the analysis pipeline.",
  );

  /* 3. Evidence statistics */
  heading(3, "Evidence Statistics");
  const entries: [string, number][] = [
    ["Messages", stats.messages],
    ["Calls", stats.calls],
    ["Audio", stats.audio],
    ["Images", stats.images],
    ["OCR results", stats.ocr],
    ["Detected objects", stats.objects],
    ["Entities", stats.entities],
    ["Flags", stats.flags],
  ];
  const colW = CONTENT / 4;
  for (let i = 0; i < entries.length; i += 4) {
    need(58);
    entries.slice(i, i + 4).forEach(([label, value], c) => {
      const x = MARGIN + c * colW;
      doc.setDrawColor(226, 226, 230);
      doc.setLineWidth(0.8);
      doc.rect(x, y, colW - 8, 46);
      doc.setFont("helvetica", "bold").setFontSize(16).setTextColor(...RED);
      doc.text(String(value), x + 10, y + 24);
      doc.setFont("helvetica", "normal").setFontSize(8).setTextColor(...GREY);
      doc.text(safe(label).toUpperCase(), x + 10, y + 38);
    });
    y += 58;
  }

  /* 4. Entities */
  heading(4, "Entities");
  if (report.entities.length === 0) para("No entities were extracted.", { color: GREY });
  report.entities.forEach((e) => {
    para(`${text(e.name, "Unnamed entity")}  —  ${text(e.type, "unknown type")}`, { bold: true });
    para(`Known contact: ${text(e.known_contact, "Not identified")}`, { size: 9, color: GREY });
    para(`Related records: ${list(e.record_ids).join(", ") || "None"}`, { size: 9, color: GREY });
    rule();
  });

  /* 5. Flags */
  heading(5, "Flags / Analysis Findings");
  if (report.flags.length === 0) para("No analysis findings were derived.", { color: GREY });
  report.flags.forEach((f) => {
    aiBlock(
      "Analysis / derived finding — not a confirmed fact",
      `${text(f.reason, "Unspecified finding")}\nSource: ${text(f.source, "unknown")}\nRecords: ${
        list(f.record_ids).join(", ") || "None"
      }`,
    );
  });

  /* 6. Timeline */
  heading(6, "Evidence Timeline");
  if (report.timeline.length === 0) para("No timeline records available.", { color: GREY });
  report.timeline.forEach((r) => {
    need(40);
    para(`[${r.id}]  ${String(r.kind).toUpperCase()}  •  ${formatTimestamp(r.timestamp)}`, {
      bold: true,
      size: 10,
      color: DARK,
    });
    if (text(r.headline)) para(text(r.headline));
    if (text(r.detail)) para(text(r.detail), { size: 9, color: GREY });
    if (text(r.transcript)) para(`Transcript: ${text(r.transcript)}`, { size: 9, indent: 12 });
    if (text(r.ocr_text)) para(`OCR text: ${text(r.ocr_text)}`, { size: 9, indent: 12 });
    if (text(r.media_uri)) para(`Media: ${text(r.media_uri)}`, { size: 8, color: GREY, indent: 12 });
    const objects = list(r.detected_objects)
      .map((o) => {
        const pct = confidencePercent(o.confidence);
        return `${text(o.label, "object")}${pct ? ` (${pct})` : ""}`;
      })
      .join(", ");
    if (objects) para(`Detected objects: ${objects}`, { size: 9, indent: 12 });
    if (text(r.caption)) aiBlock("AI caption — unverified", text(r.caption));
    rule();
  });

  need(40);
  para(`Report generated ${generatedAt} by ${meta.analyst}.`, { size: 9, color: GREY });
  footer();

  return doc.output("blob");
}

export const pdfFileName = (caseId: string) =>
  `${caseId || "case"}-forensic-report.pdf`.replace(/\s+/g, "-");
