import { ListTree, SearchX } from "lucide-react";
import type { TimelineRecord } from "@/lib/report-types";
import { Panel, SectionLabel } from "./primitives";
import { TimelineItem } from "./TimelineItem";

export function Timeline({
  records,
  onClearFilters,
  hasFilters,
}: {
  records: TimelineRecord[];
  onClearFilters: () => void;
  hasFilters: boolean;
}) {
  return (
    <Panel>
      <SectionLabel
        icon={<ListTree className="h-4 w-4 text-brand-deep" aria-hidden />}
        right={<span className="font-mono text-xs text-muted-foreground">{records.length}</span>}
      >
        Evidence Timeline
      </SectionLabel>

      {records.length === 0 ? (
        <div className="flex flex-col items-center px-6 py-16 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-full border border-border bg-muted text-muted-foreground">
            <SearchX className="h-6 w-6" aria-hidden />
          </span>
          <p className="mt-4 text-sm font-medium text-foreground">
            No evidence matches your current filters.
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Adjust your search terms or clear the active entity filter.
          </p>
          {hasFilters && (
            <button
              type="button"
              onClick={onClearFilters}
              className="focus-ring mt-4 inline-flex h-10 items-center rounded-lg bg-brand-deep px-4 text-sm font-semibold text-primary-foreground transition-colors hover:bg-brand-dark"
            >
              Clear Filters
            </button>
          )}
        </div>
      ) : (
        <ol className="space-y-5 p-4 sm:p-5">
          {records.map((record) => (
            <TimelineItem key={record.id} record={record} />
          ))}
        </ol>
      )}
    </Panel>
  );
}
