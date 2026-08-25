import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Loader2, AlertTriangle, FolderGit2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { SearchBar } from "@/components/forensics/SearchBar";
import { Timeline } from "@/components/forensics/Timeline";
import { FilterBar } from "@/components/forensics/FilterBar";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { useReport, filterRecords, entityRecordIds } from "@/lib/use-report";
import { useInvestigation } from "@/lib/investigation";
import { timestampValue, text, type TimelineRecord } from "@/lib/report-types";
import {
  getMessages,
  getCalls,
  getMedia,
  getOcrResults,
  getTranscriptions,
  getImageAnalysis,
  getImageTags,
  getMediaFileUrl,
  formatFileSize,
  type MessageRecord,
  type CallRecord,
  type MediaRecord,
  type OcrResultRecord,
  type TranscriptionRecord,
  type ImageAnalysisRecord,
  type ImageTagRecord,
} from "@/services/forensics-api";

const title = "Evidence Timeline — Evidence Examiner Desk";
const description =
  "Chronological investigation of all evidence — messages, calls, images, documents and audio — with full-text search across OCR, transcripts, AI captions and detected objects.";

export const Route = createFileRoute("/_shell/timeline")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: TimelinePage,
});

function TimelinePage() {
  const { activeCaseId } = useInvestigation();
  const report = useReport();

  const [entityIndex, setEntityIndex] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<string | null>(null);

  const [messages, setMessages] = useState<MessageRecord[]>([]);
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [mediaList, setMediaList] = useState<MediaRecord[]>([]);
  const [ocrList, setOcrList] = useState<OcrResultRecord[]>([]);
  const [transcriptionList, setTranscriptionList] = useState<TranscriptionRecord[]>([]);
  const [analysisList, setAnalysisList] = useState<ImageAnalysisRecord[]>([]);
  const [tagList, setTagList] = useState<ImageTagRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeCaseId === null) return;
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      getMessages(activeCaseId),
      getCalls(activeCaseId),
      getMedia(activeCaseId),
      getOcrResults(activeCaseId),
      getTranscriptions(activeCaseId),
      getImageAnalysis(activeCaseId),
      getImageTags(activeCaseId),
    ])
      .then(([msgData, callData, mediaData, ocrData, tData, iaData, tagData]) => {
        if (mounted) {
          setMessages(msgData);
          setCalls(callData);
          setMediaList(mediaData);
          setOcrList(ocrData);
          setTranscriptionList(tData);
          setAnalysisList(iaData);
          setTagList(tagData);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load timeline records.");
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [activeCaseId]);

  const realTimelineRecords: TimelineRecord[] = useMemo(() => {
    // Messages
    const msgEvents: TimelineRecord[] = messages.map((m) => ({
      id: m.message_id || `MSG-${m.id}`,
      kind: "message",
      timestamp: m.timestamp,
      headline: `${m.sender || "Unknown"} → ${m.receiver || "Unknown"}`,
      detail: m.text || "No text content",
    }));

    // Calls
    const callEvents: TimelineRecord[] = calls.map((c) => ({
      id: c.call_id || `CALL-${c.id}`,
      kind: "call",
      timestamp: c.timestamp,
      headline: `${c.type ? (c.type.charAt(0).toUpperCase() + c.type.slice(1)) : "Call"} ${c.caller || "Unknown"} → ${c.callee || "Unknown"}`,
      detail: `Duration: ${c.duration_seconds != null ? `${c.duration_seconds}s` : "Unknown"} · Type: ${c.type || "unknown"}`,
    }));

    // Media (images, documents, audio) — enriched with OCR / transcript / caption / tags
    const mediaEvents: TimelineRecord[] = mediaList.map((m) => {
      const ocr = ocrList.find((o) => o.media_id === m.id);
      const tr = transcriptionList.find((t) => t.media_id === m.id);
      const ia = analysisList.find((a) => a.media_id === m.id);
      const tags = tagList.filter((t) => t.media_id === m.id);

      const rawKind = m.type ? m.type.toLowerCase() : "image";
      // Keep "document" as its own kind so FilterBar can filter it separately
      const kind = rawKind === "document" ? "document" : rawKind === "audio" ? "audio" : "image";

      const detail = [
        formatFileSize(m.file_size_bytes || 0),
        `Status: ${m.status || "PARSED"}`,
        m.sha256 ? `SHA256: ${m.sha256.slice(0, 16)}...` : null,
        m.associated_message_id ? `Message: ${m.associated_message_id}` : null,
        m.associated_call_id ? `Call: ${m.associated_call_id}` : null,
        tags.length > 0 ? `Objects: ${tags.map((t) => t.tag).join(", ")}` : null,
      ]
        .filter(Boolean)
        .join(" · ");

      return {
        id: m.media_id || `MED-${m.id}`,
        kind,
        timestamp: m.timestamp,
        headline: m.filename,
        detail,
        media_uri: getMediaFileUrl(m.id),
        ocr_text: ocr ? (ocr.translated_text || ocr.text) : null,
        transcript: tr ? tr.text : null,
        caption: ia
          ? ia.context ||
            (ia.width && ia.height ? `${ia.width}×${ia.height} ${ia.format || ""}`.trim() : null)
          : null,
        caption_status: ia ? "verified" : null,
        detected_objects: tags.map((t) => ({ label: t.tag, confidence: t.confidence })),
      };
    });

    const combined = [...msgEvents, ...callEvents, ...mediaEvents];
    combined.sort((a, b) => timestampValue(a.timestamp) - timestampValue(b.timestamp));
    return combined;
  }, [messages, calls, mediaList, ocrList, transcriptionList, analysisList, tagList]);

  const activeEntity = entityIndex !== null ? report.entities[entityIndex] : undefined;

  const visibleRecords = useMemo(() => {
    const ids = activeEntity ? entityRecordIds(activeEntity) : null;
    const base = filterRecords(realTimelineRecords, query, ids);
    return kind ? base.filter((r) => text(r.kind).toLowerCase() === kind) : base;
  }, [realTimelineRecords, activeEntity, query, kind]);

  const hasFilters = entityIndex !== null || query.trim().length > 0 || kind !== null;

  const clearFilters = () => {
    setEntityIndex(null);
    setQuery("");
    setKind(null);
  };

  const totalMedia = mediaList.length;

  return (
    <>
      <PageHeader
        title="Evidence Timeline"
        description="All evidence — messages, calls, images, documents and audio — in chronological order. Search across text, OCR, transcripts, captions and detected objects."
      />

      <div className="space-y-4">
        {/* Active Case Notification */}
        <Panel>
          <SectionLabel
            icon={<FolderGit2 className="h-4 w-4 text-brand-deep" aria-hidden />}
            right={
              <span className="text-xs font-medium text-muted-foreground">
                Case #{activeCaseId ?? "-"} Active
              </span>
            }
          >
            Case #{activeCaseId ?? "-"} — {messages.length} Messages · {calls.length} Calls · {totalMedia} Media Items
          </SectionLabel>

          {loading && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Loading all evidence from PostgreSQL...
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 border-l-4 border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </Panel>

        <SearchBar
          query={query}
          onQueryChange={setQuery}
          onClearFilters={clearFilters}
          hasFilters={hasFilters}
          visibleCount={visibleRecords.length}
          totalCount={realTimelineRecords.length}
          activeEntity={activeEntity ? text(activeEntity.name, "Selected") : null}
        />

        <FilterBar
          entities={report.entities}
          activeEntity={entityIndex}
          onEntityChange={setEntityIndex}
          activeKind={kind}
          onKindChange={setKind}
        />

        <Timeline
          records={visibleRecords}
          hasFilters={hasFilters}
          onClearFilters={clearFilters}
        />
      </div>
    </>
  );
}
