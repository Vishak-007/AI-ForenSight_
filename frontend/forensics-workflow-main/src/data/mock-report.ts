import type { ReportData } from "@/lib/report-types";
import parkingImage from "@/assets/evidence-parking.jpg";
import noteImage from "@/assets/evidence-note.jpg";

/**
 * Mock dataset matching the report_data.json contract exactly.
 * Replace with the generated file (see src/data/report-source.ts).
 */
export const mockReport: ReportData = {
  device_id: "DEV-0472-A",
  overall_summary:
    "Analysis of device DEV-0472-A recovered 14 correlated evidence records spanning a 16-hour window on 24 August 2026. Communications indicate coordination between the device owner (identified contact: John Smith) and at least two additional parties regarding a meeting at a dock location during late evening hours. Two voice recordings reference cash handling and instructions to avoid written communication. Recovered imagery places two individuals near a vehicle in a parking structure approximately 40 minutes after the referenced meeting time. Several deleted-message artifacts were recovered from unallocated space and correlate with the same contact identifiers.",
  entities: [
    {
      name: "John",
      type: "person",
      known_contact: "John Smith (+1 415 555 0142)",
      record_ids: ["M001", "C001", "M004", "MED002", "M007"],
    },
    {
      name: "Alice",
      type: "person",
      known_contact: "Alice Moreno (+1 415 555 0198)",
      record_ids: ["M001", "M002", "C002", "MED001"],
    },
    {
      name: "Unknown Caller",
      type: "phone",
      known_contact: null,
      record_ids: ["C003", "MED003"],
    },
    {
      name: "Dock 4 Terminal",
      type: "location",
      known_contact: "Port Access Road, Bay 4",
      record_ids: ["M004", "MED001", "M007", "MED004"],
    },
    {
      name: "cash_drop_2608",
      type: "keyword",
      known_contact: null,
      record_ids: ["M002", "MED002", "M006"],
    },
  ],
  flags: [
    {
      reason: "Repeated references to an unrecorded cash handover between two parties.",
      source: "message",
      record_ids: ["M002", "M006"],
    },
    {
      reason: "Instruction to avoid written communication, consistent with anti-forensic behaviour.",
      source: "audio",
      record_ids: ["MED002"],
    },
    {
      reason: "Deleted message artifact recovered from unallocated space.",
      source: "message",
      record_ids: ["M007"],
    },
    {
      reason: "Late-night call from an unregistered number immediately preceding imagery capture.",
      source: "call",
      record_ids: ["C003", "MED003"],
    },
  ],
  timeline: [
    {
      id: "M001",
      kind: "message",
      timestamp: "2026-08-24T08:12:00",
      headline: "John → Alice",
      detail: "Are we still on for tonight? Don't reply here if you're not alone.",
    },
    {
      id: "C001",
      kind: "call",
      timestamp: "2026-08-24T08:41:00",
      headline: "Outgoing call to John Smith (+1 415 555 0142)",
      detail: "Duration 4m 12s · Cellular · Tower ID 44219 (Downtown East)",
    },
    {
      id: "M002",
      kind: "message",
      timestamp: "2026-08-24T09:05:00",
      headline: "Alice → Device owner",
      detail: "Bring the full amount in cash. No transfers, nothing traceable.",
    },
    {
      id: "MED002",
      kind: "audio",
      timestamp: "2026-08-24T10:22:00",
      headline: "Recorded voice memo · rec-001.wav",
      detail: "Duration 6s (excerpt) · 16 kHz mono · Recovered from /media/audio",
      transcript:
        "…tell him the amount stays the same. Do not put any of this in writing, we talk in person only. I will be at the usual place after eight.",
      media_uri: "/audio/rec-001.wav",
    },
    {
      id: "C002",
      kind: "call",
      timestamp: "2026-08-24T11:47:00",
      headline: "Missed call from Alice Moreno (+1 415 555 0198)",
      detail: "Duration 0s · Missed · Two callback attempts within 6 minutes",
    },
    {
      id: "M004",
      kind: "message",
      timestamp: "2026-08-24T13:30:00",
      headline: "John → Device owner",
      detail: "Dock 4, back gate. It stays open until half past eight.",
    },
    {
      id: "MED004",
      kind: "image",
      timestamp: "2026-08-24T14:02:00",
      headline: "Photographed handwritten note",
      detail: "3024 × 1890 JPEG · Camera roll · EXIF GPS stripped",
      media_uri: noteImage,
      ocr_text: "MEETING AT 8PM DOCK 4",
      detected_objects: [
        { label: "paper", confidence: 0.96 },
        { label: "handwriting", confidence: 0.91 },
        { label: "table", confidence: 0.84 },
      ],
      caption: "A crumpled handwritten note on a wooden table stating a meeting time and location.",
      caption_status: "unverified",
    },
    {
      id: "M005",
      kind: "message",
      timestamp: "2026-08-24T15:10:00",
      headline: "Device owner → Alice",
      detail: "Understood. I'll come alone.",
    },
    {
      id: "C003",
      kind: "call",
      timestamp: "2026-08-24T19:58:00",
      headline: "Incoming call from unregistered number (+1 415 555 0007)",
      detail: "Duration 1m 03s · Number not present in contacts · Carrier lookup inconclusive",
    },
    {
      id: "MED003",
      kind: "audio",
      timestamp: "2026-08-24T20:14:00",
      headline: "Ambient recording · rec-002.wav",
      detail: "Duration 6s (excerpt) · Background noise consistent with an outdoor industrial area",
      transcript: null,
      media_uri: "/audio/rec-002.wav",
    },
    {
      id: "M006",
      kind: "message",
      timestamp: "2026-08-24T20:31:00",
      headline: "Device owner → John",
      detail: "Cash is counted. Waiting at the gate.",
    },
    {
      id: "MED001",
      kind: "image",
      timestamp: "2026-08-24T20:42:00",
      headline: "Surveillance still recovered from cache",
      detail: "1024 × 640 JPEG · Recovered from application cache directory",
      media_uri: parkingImage,
      ocr_text: "20157/167",
      detected_objects: [
        { label: "person", confidence: 0.97 },
        { label: "car", confidence: 0.88 },
        { label: "bag", confidence: 0.63 },
      ],
      caption: "Two people standing beside a dark sedan in a dimly lit parking structure at night.",
      caption_status: "unverified",
    },
    {
      id: "M007",
      kind: "message",
      timestamp: "2026-08-24T21:16:00",
      headline: "John → Device owner (deleted, recovered)",
      detail: "Delete this thread when you get home. Dock 4 never happened.",
    },
    {
      id: "C004",
      kind: "call",
      timestamp: "2026-08-24T23:49:00",
      headline: "Outgoing call to voicemail service",
      detail: "Duration 0m 22s · No recording retained on device",
    },
  ],
};
