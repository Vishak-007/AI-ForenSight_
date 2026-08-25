import { useState } from "react";
import { MessageSquare, PhoneCall, AudioLines, ImageIcon, Clock, ImageOff } from "lucide-react";
import type { DetectedObject, TimelineRecord } from "@/lib/report-types";
import { confidencePercent, formatTimestamp, list, text } from "@/lib/report-types";
import { KindBadge, RecordId } from "./primitives";
import { EvidenceBlock } from "./EvidenceBlock";
import { AiCaption } from "./AiCaption";

const KIND_META: Record<string, { icon: typeof MessageSquare; label: string }> = {
  message: { icon: MessageSquare, label: "Message" },
  call: { icon: PhoneCall, label: "Call" },
  audio: { icon: AudioLines, label: "Audio" },
  image: { icon: ImageIcon, label: "Image" },
};

function Shell({ record, children }: { record: TimelineRecord; children?: React.ReactNode }) {
  const kind = text(record.kind, "record").toLowerCase();
  const meta = KIND_META[kind];
  const Icon = meta?.icon ?? Clock;
  const headline = text(record.headline, "Untitled record");
  const detail = text(record.detail);

  return (
    <li className="animate-fade-rise relative pl-10 sm:pl-14">
      <span
        aria-hidden
        className="absolute left-[13px] top-9 bottom-[-1.25rem] w-px bg-border sm:left-[21px]"
      />
      <span className="absolute left-0 top-3 grid h-7 w-7 place-items-center rounded-full border-2 border-brand-deep bg-card text-brand-deep sm:h-11 sm:w-11">
        <Icon className="h-3.5 w-3.5 sm:h-5 sm:w-5" aria-hidden />
      </span>

      <article className="rounded-xl border border-evidence-border bg-evidence p-4 shadow-card transition-shadow hover:shadow-raised">
        <div className="flex flex-wrap items-center gap-2">
          <KindBadge kind={meta?.label ?? kind} />
          <RecordId id={record.id} />
          <span className="ml-auto flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" aria-hidden />
            {formatTimestamp(record.timestamp)}
          </span>
        </div>

        <h3 className="mt-3 text-base font-semibold leading-snug text-foreground">{headline}</h3>
        {detail && <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{detail}</p>}
        {children}
      </article>
    </li>
  );
}

function ObjectTags({ objects }: { objects: DetectedObject[] }) {
  const valid = objects.filter((o) => text(o?.label));
  if (valid.length === 0) return null;

  return (
    <EvidenceBlock label="Detected Objects">
      <div className="flex flex-wrap gap-1.5">
        {valid.map((o, i) => {
          const pct = confidencePercent(o.confidence);
          return (
            <span
              key={`${o.label}-${i}`}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted px-2 py-1 font-mono text-xs text-foreground"
            >
              {text(o.label)}
              {pct && <span className="font-semibold text-brand-deep">{pct}</span>}
            </span>
          );
        })}
      </div>
    </EvidenceBlock>
  );
}

function AudioBody({ record }: { record: TimelineRecord }) {
  const src = text(record.media_uri);
  const transcript = text(record.transcript);

  return (
    <>
      {src ? (
        <div className="mt-3 rounded-lg border border-evidence-border bg-muted/60 p-3">
          <p className="label-caps mb-2 text-muted-foreground">Audio Evidence</p>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio controls preload="none" src={src} className="w-full">
            Your browser does not support audio playback.
          </audio>
        </div>
      ) : (
        <p className="mt-3 rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
          Audio media unavailable for this record.
        </p>
      )}
      {transcript && <EvidenceBlock label="Transcript">{transcript}</EvidenceBlock>}
    </>
  );
}

function ImageBody({ record }: { record: TimelineRecord }) {
  const src = text(record.media_uri);
  const [failed, setFailed] = useState(false);
  const ocr = text(record.ocr_text);
  const objects = list(record.detected_objects);

  return (
    <>
      {src && !failed ? (
        <div className="mt-3 overflow-hidden rounded-lg border border-evidence-border bg-muted">
          <img
            src={src}
            alt={`Image evidence ${record.id}: ${text(record.headline, "recovered image")}`}
            loading="lazy"
            onError={() => setFailed(true)}
            className="max-h-[420px] w-full object-cover"
          />
        </div>
      ) : (
        <p className="mt-3 flex items-center gap-2 rounded-lg border border-dashed border-border px-3 py-3 text-xs text-muted-foreground">
          <ImageOff className="h-4 w-4" aria-hidden />
          Image media unavailable for this record.
        </p>
      )}
      <ObjectTags objects={objects} />
      {ocr && (
        <EvidenceBlock label="OCR Extracted Text">
          <span className="font-mono">{ocr}</span>
        </EvidenceBlock>
      )}
      <AiCaption caption={record.caption} status={record.caption_status} />
    </>
  );
}

export function TimelineItem({ record }: { record: TimelineRecord }) {
  const kind = text(record.kind).toLowerCase();

  if (kind === "audio") {
    return (
      <Shell record={record}>
        <AudioBody record={record} />
      </Shell>
    );
  }
  if (kind === "image") {
    return (
      <Shell record={record}>
        <ImageBody record={record} />
      </Shell>
    );
  }
  if (kind === "call") {
    return (
      <Shell record={record}>
        <div className="mt-3 h-px w-full bg-border" />
        <p className="mt-2 label-caps text-muted-foreground">Call log entry · raw evidence</p>
      </Shell>
    );
  }
  return <Shell record={record} />;
}
