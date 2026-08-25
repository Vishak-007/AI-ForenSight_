import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { ImageIcon, AudioLines, ImageOff, FolderGit2, Loader2, AlertTriangle, FileText, Layers } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Panel, RecordId, SectionLabel } from "@/components/forensics/primitives";
import { TimelineItem } from "@/components/forensics/TimelineItem";
import { useReport } from "@/lib/use-report";
import { useInvestigation } from "@/lib/investigation";
import { formatTimestamp, text, type TimelineRecord } from "@/lib/report-types";
import { cn } from "@/lib/utils";
import {
  getMedia,
  getOcrResults,
  getTranscriptions,
  getImageAnalysis,
  getImageTags,
  formatFileSize,
  type MediaRecord,
  type OcrResultRecord,
  type TranscriptionRecord,
  type ImageAnalysisRecord,
  type ImageTagRecord,
} from "@/services/forensics-api";

const title = "Media Evidence — Evidence Examiner Desk";
const description =
  "Inspect recovered image and audio evidence with previews, playback, OCR text, detected objects, transcripts and clearly labelled AI captions.";

export const Route = createFileRoute("/_shell/media")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: MediaPage,
});

type Tab = "image" | "audio" | "all";

function MediaPage() {
  const { activeCaseId } = useInvestigation();
  const report = useReport();
  const [tab, setTab] = useState<Tab>("image");
  const [selectedId, setSelectedId] = useState<string | null>(null);

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
      getMedia(activeCaseId),
      getOcrResults(activeCaseId),
      getTranscriptions(activeCaseId),
      getImageAnalysis(activeCaseId),
      getImageTags(activeCaseId),
    ])
      .then(([mRes, ocrRes, tRes, iaRes, tagRes]) => {
        if (mounted) {
          setMediaList(mRes);
          setOcrList(ocrRes);
          setTranscriptionList(tRes);
          setAnalysisList(iaRes);
          setTagList(tagRes);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load media evidence.");
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [activeCaseId]);

  const realMediaRecords: TimelineRecord[] = useMemo(() => {
    return mediaList.map((m) => {
      const ocr = ocrList.find((o) => o.media_id === m.id);
      const tr = transcriptionList.find((t) => t.media_id === m.id);
      const ia = analysisList.find((a) => a.media_id === m.id);
      const tags = tagList.filter((t) => t.media_id === m.id);

      let kind = m.type ? m.type.toLowerCase() : "image";
      if (kind === "document") kind = "image"; // documents render image/OCR metadata

      const headline = m.filename;
      const detail = `${formatFileSize(m.file_size_bytes || 0)} · Status: ${m.status || "PARSED"}${
        m.sha256 ? ` · SHA256: ${m.sha256.slice(0, 16)}...` : ""
      }${m.associated_message_id ? ` · Message: ${m.associated_message_id}` : ""}${
        m.associated_call_id ? ` · Call: ${m.associated_call_id}` : ""
      }`;

      return {
        id: m.media_id || `MED-${m.id}`,
        kind: kind,
        timestamp: m.timestamp,
        headline: headline,
        detail: detail,
        media_uri: null, // safe placeholder until media serving API is built
        ocr_text: ocr ? ocr.text : null,
        transcript: tr ? tr.text : null,
        caption: ia ? (ia.context || (ia.width && ia.height ? `${ia.width}x${ia.height} ${ia.format || ""}` : null)) : null,
        caption_status: ia ? "verified" : null,
        detected_objects: tags.map((t) => ({ label: t.tag, confidence: t.confidence })),
      };
    });
  }, [mediaList, ocrList, transcriptionList, analysisList, tagList]);

  const items = useMemo(() => {
    if (tab === "all") return realMediaRecords;
    return realMediaRecords.filter((r) => text(r.kind).toLowerCase() === tab);
  }, [realMediaRecords, tab]);

  const selected = items.find((r) => r.id === selectedId) ?? items[0];

  const tabs: { value: Tab; label: string; icon: typeof ImageIcon }[] = [
    { value: "image", label: "Images & Documents", icon: ImageIcon },
    { value: "audio", label: "Audio", icon: AudioLines },
    { value: "all", label: "All Media", icon: Layers },
  ];

  return (
    <>
      <PageHeader
        title="Media Evidence"
        description="Recovered images, audio recordings, OCR, and AI image analysis from PostgreSQL."
      />

      {/* Active Case Notification */}
      <div className="mb-4">
        <Panel>
          <SectionLabel
            icon={<FolderGit2 className="h-4 w-4 text-brand-deep" aria-hidden />}
            right={
              <span className="text-xs font-medium text-muted-foreground">
                Case #{activeCaseId ?? "-"} Active
              </span>
            }
          >
            Active Case #{activeCaseId ?? "-"} Media ({mediaList.length} Items, {ocrList.length} OCR, {transcriptionList.length} Transcripts, {analysisList.length} Image Analyses, {tagList.length} Tags)
          </SectionLabel>

          {loading && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Loading real media and analysis data from PostgreSQL...
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 border-l-4 border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </Panel>
      </div>

      <div className="mb-4 inline-flex rounded-lg border border-border bg-card p-1 shadow-card">
        {tabs.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => {
              setTab(t.value);
              setSelectedId(null);
            }}
            aria-pressed={tab === t.value}
            className={cn(
              "focus-ring inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors",
              tab === t.value
                ? "bg-brand-deep text-primary-foreground"
                : "text-muted-foreground hover:bg-ai hover:text-brand-dark",
            )}
          >
            <t.icon className="h-4 w-4" aria-hidden />
            {t.label}
          </button>
        ))}
      </div>

      {!loading && !error && items.length === 0 ? (
        <Panel>
          <p className="px-4 py-12 text-center text-sm text-muted-foreground">
            No {tab} evidence was recovered for Case #{activeCaseId}.
          </p>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
          <ul className="space-y-3">
            {items.map((record) => {
              const active = selected?.id === record.id;
              const src = text(record.media_uri);
              return (
                <li key={record.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(record.id)}
                    aria-pressed={active}
                    className={cn(
                      "focus-ring flex w-full items-center gap-3 rounded-xl border p-3 text-left shadow-card transition-colors",
                      active
                        ? "border-brand-deep bg-ai"
                        : "border-border bg-card hover:border-brand-accent hover:bg-ai/60",
                    )}
                  >
                    <span className="grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-lg border border-border bg-muted text-muted-foreground">
                      {tab === "image" && src ? (
                        <img
                          src={src}
                          alt=""
                          loading="lazy"
                          className="h-full w-full object-cover"
                        />
                      ) : tab === "audio" ? (
                        <AudioLines className="h-5 w-5" aria-hidden />
                      ) : (
                        <ImageIcon className="h-5 w-5 text-brand-deep" aria-hidden />
                      )}
                    </span>
                    <span className="min-w-0 flex-1">
                      <RecordId id={record.id} tone={active ? "red" : "neutral"} />
                      <span className="mt-1 block truncate text-sm font-semibold text-foreground">
                        {text(record.headline, "Untitled media")}
                      </span>
                      <span className="block truncate font-mono text-xs text-muted-foreground">
                        {formatTimestamp(record.timestamp)}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <Panel className="lg:sticky lg:top-24 lg:self-start">
            <SectionLabel
              icon={
                tab === "image" ? (
                  <ImageIcon className="h-4 w-4 text-brand-deep" aria-hidden />
                ) : (
                  <AudioLines className="h-4 w-4 text-brand-deep" aria-hidden />
                )
              }
              right={selected ? <RecordId id={selected.id} /> : null}
            >
              Media Details
            </SectionLabel>
            {selected ? (
              <ol className="p-4">
                <TimelineItem record={selected} />
              </ol>
            ) : (
              <p className="px-4 py-12 text-center text-sm text-muted-foreground">
                Select a media item to inspect its details.
              </p>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}

