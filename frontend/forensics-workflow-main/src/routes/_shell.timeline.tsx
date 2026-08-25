import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Loader2, AlertTriangle, MessageSquare, PhoneCall, FolderGit2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { SearchBar } from "@/components/forensics/SearchBar";
import { Timeline } from "@/components/forensics/Timeline";
import { FilterBar } from "@/components/forensics/FilterBar";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { useReport, filterRecords, entityRecordIds } from "@/lib/use-report";
import { useInvestigation } from "@/lib/investigation";
import { timestampValue, text, type TimelineRecord } from "@/lib/report-types";
import { getMessages, getCalls, type MessageRecord, type CallRecord } from "@/services/forensics-api";

const title = "Evidence Timeline — Evidence Examiner Desk";
const description =
  "Chronological investigation of message, call, audio and image evidence with search, entity filtering, transcripts, OCR and detected objects.";

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
    ])
      .then(([msgData, callData]) => {
        if (mounted) {
          setMessages(msgData);
          setCalls(callData);
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
    const msgEvents: TimelineRecord[] = messages.map((m) => ({
      id: m.message_id || `MSG-${m.id}`,
      kind: "message",
      timestamp: m.timestamp,
      headline: `${m.sender || "Unknown"} → ${m.receiver || "Unknown"}`,
      detail: m.text || "No text content",
    }));

    const callEvents: TimelineRecord[] = calls.map((c) => ({
      id: c.call_id || `CALL-${c.id}`,
      kind: "call",
      timestamp: c.timestamp,
      headline: `${c.type ? (c.type.charAt(0).toUpperCase() + c.type.slice(1)) : "Call"} ${c.caller || "Unknown"} → ${c.callee || "Unknown"}`,
      detail: `Duration: ${c.duration_seconds != null ? `${c.duration_seconds}s` : "Unknown"} · Type: ${c.type || "unknown"}`,
    }));

    const combined = [...msgEvents, ...callEvents];
    combined.sort((a, b) => timestampValue(a.timestamp) - timestampValue(b.timestamp));
    return combined;
  }, [messages, calls]);

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

  return (
    <>
      <PageHeader
        title="Evidence Timeline"
        description="Raw extracted messages and calls in chronological order from PostgreSQL."
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
            Active Case #{activeCaseId ?? "-"} Timeline ({messages.length} Messages, {calls.length} Calls)
          </SectionLabel>

          {loading && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Loading real messages and calls from PostgreSQL...
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

