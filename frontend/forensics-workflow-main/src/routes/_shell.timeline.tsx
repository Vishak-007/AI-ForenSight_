import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { SearchBar } from "@/components/forensics/SearchBar";
import { Timeline } from "@/components/forensics/Timeline";
import { FilterBar } from "@/components/forensics/FilterBar";
import { useReport, filterRecords, entityRecordIds } from "@/lib/use-report";
import { text } from "@/lib/report-types";

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
  const report = useReport();
  const [entityIndex, setEntityIndex] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<string | null>(null);

  const activeEntity = entityIndex !== null ? report.entities[entityIndex] : undefined;

  const visibleRecords = useMemo(() => {
    const ids = activeEntity ? entityRecordIds(activeEntity) : null;
    const base = filterRecords(report.timeline, query, ids);
    return kind ? base.filter((r) => text(r.kind).toLowerCase() === kind) : base;
  }, [report.timeline, activeEntity, query, kind]);

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
        description="Raw extracted evidence in chronological order. AI-derived content is shown separately on red-bordered surfaces."
      />

      <div className="space-y-4">
        <SearchBar
          query={query}
          onQueryChange={setQuery}
          onClearFilters={clearFilters}
          hasFilters={hasFilters}
          visibleCount={visibleRecords.length}
          totalCount={report.timeline.length}
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
