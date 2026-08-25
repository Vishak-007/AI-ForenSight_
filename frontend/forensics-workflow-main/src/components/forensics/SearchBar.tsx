import { Search, X, FilterX } from "lucide-react";

export function SearchBar({
  query,
  onQueryChange,
  onClearFilters,
  hasFilters,
  visibleCount,
  totalCount,
  activeEntity,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  onClearFilters: () => void;
  hasFilters: boolean;
  visibleCount: number;
  totalCount: number;
  activeEntity: string | null;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-3 shadow-card sm:p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative min-w-0 flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search all evidence — messages, filenames, OCR text, transcripts, objects..."
            aria-label="Search all evidence"
            className="focus-ring h-12 w-full rounded-lg border border-input bg-background pl-11 pr-10 text-base text-foreground placeholder:text-muted-foreground focus:border-brand-accent"
          />
          {query.length > 0 && (
            <button
              type="button"
              onClick={() => onQueryChange("")}
              aria-label="Clear search text"
              className="focus-ring absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={onClearFilters}
          disabled={!hasFilters}
          className="focus-ring inline-flex h-12 shrink-0 items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:border-brand-accent hover:bg-ai hover:text-brand-dark disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:border-border disabled:hover:bg-card disabled:hover:text-foreground"
        >
          <FilterX className="h-4 w-4" aria-hidden />
          Clear Filters
        </button>
      </div>

      <div
        aria-live="polite"
        className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground"
      >
        <span>
          Showing <span className="font-semibold text-foreground">{visibleCount}</span> of{" "}
          <span className="font-semibold text-foreground">{totalCount}</span> evidence items
        </span>
        {activeEntity && (
          <span className="label-caps rounded-md border border-ai-border bg-ai px-2 py-0.5 text-brand-dark">
            Entity: {activeEntity}
          </span>
        )}
      </div>
    </section>
  );
}
