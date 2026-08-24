import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { ImageIcon, AudioLines, ImageOff } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Panel, RecordId, SectionLabel } from "@/components/forensics/primitives";
import { TimelineItem } from "@/components/forensics/TimelineItem";
import { useReport } from "@/lib/use-report";
import { formatTimestamp, text } from "@/lib/report-types";
import { cn } from "@/lib/utils";

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

type Tab = "image" | "audio";

function MediaPage() {
  const report = useReport();
  const [tab, setTab] = useState<Tab>("image");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const items = useMemo(
    () => report.timeline.filter((r) => text(r.kind).toLowerCase() === tab),
    [report.timeline, tab],
  );

  const selected = items.find((r) => r.id === selectedId) ?? items[0];

  const tabs: { value: Tab; label: string; icon: typeof ImageIcon }[] = [
    { value: "image", label: "Images", icon: ImageIcon },
    { value: "audio", label: "Audio", icon: AudioLines },
  ];

  return (
    <>
      <PageHeader
        title="Media Evidence"
        description="Recovered images and audio recordings with their extracted analysis artefacts."
      />

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

      {items.length === 0 ? (
        <Panel>
          <p className="px-4 py-12 text-center text-sm text-muted-foreground">
            No {tab} evidence was recovered from this device.
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
                        <ImageOff className="h-5 w-5" aria-hidden />
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
