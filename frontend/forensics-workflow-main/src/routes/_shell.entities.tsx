import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { User, Phone, MapPin, Tag, Hash, Building2, X } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Panel, RecordId, SectionLabel } from "@/components/forensics/primitives";
import { TimelineItem } from "@/components/forensics/TimelineItem";
import { useReport, entityRecordIds, recordsByIds } from "@/lib/use-report";
import { text } from "@/lib/report-types";
import { cn } from "@/lib/utils";

const title = "Entities — Evidence Examiner Desk";
const description =
  "Investigate correlated people, phone numbers, organizations and locations extracted from the device, with linked evidence records.";

export const Route = createFileRoute("/_shell/entities")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: EntitiesPage,
});

const iconFor = (type: string) => {
  switch (type.toLowerCase()) {
    case "person":
      return User;
    case "phone":
      return Phone;
    case "location":
      return MapPin;
    case "organization":
    case "org":
      return Building2;
    case "keyword":
      return Tag;
    default:
      return Hash;
  }
};

function EntitiesPage() {
  const report = useReport();
  const [selected, setSelected] = useState<number | null>(null);

  const entity = selected !== null ? report.entities[selected] : undefined;
  const relatedIds = entityRecordIds(entity);
  const related = recordsByIds(report.timeline, relatedIds);

  return (
    <>
      <PageHeader
        title="Entities"
        description="People, phones, organizations and locations correlated across the evidence set."
      />

      {report.entities.length === 0 ? (
        <Panel>
          <p className="px-4 py-12 text-center text-sm text-muted-foreground">
            No entities were extracted from this device.
          </p>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
          <ul className="space-y-3">
            {report.entities.map((e, index) => {
              const Icon = iconFor(text(e.type, "unknown"));
              const ids = entityRecordIds(e);
              const active = selected === index;
              return (
                <li key={`${text(e.name, "entity")}-${index}`}>
                  <button
                    type="button"
                    onClick={() => setSelected(active ? null : index)}
                    aria-pressed={active}
                    className={cn(
                      "focus-ring group w-full rounded-xl border p-4 text-left shadow-card transition-colors",
                      active
                        ? "border-brand-deep bg-ai"
                        : "border-border bg-card hover:border-brand-accent hover:bg-ai/60",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <span
                        className={cn(
                          "grid h-9 w-9 shrink-0 place-items-center rounded-lg",
                          active
                            ? "bg-brand-deep text-primary-foreground"
                            : "bg-muted text-muted-foreground group-hover:bg-ai group-hover:text-brand-deep",
                        )}
                      >
                        <Icon className="h-4 w-4" aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="label-caps text-muted-foreground">
                          {text(e.type, "unknown")}
                        </p>
                        <p className="mt-0.5 truncate text-sm font-semibold text-foreground">
                          {text(e.name, "Unnamed entity")}
                        </p>
                        {text(e.known_contact) && (
                          <p className="mt-0.5 truncate text-xs text-muted-foreground">
                            {text(e.known_contact)}
                          </p>
                        )}
                        <p className="mt-2 inline-block rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] font-medium text-muted-foreground">
                          {ids.length} linked {ids.length === 1 ? "record" : "records"}
                        </p>
                        {ids.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {ids.map((id) => (
                              <RecordId key={id} id={id} tone={active ? "red" : "neutral"} />
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          <Panel className="lg:sticky lg:top-24 lg:self-start">
            <SectionLabel
              icon={<User className="h-4 w-4 text-brand-deep" aria-hidden />}
              right={
                entity ? (
                  <button
                    type="button"
                    onClick={() => setSelected(null)}
                    aria-label="Clear entity selection"
                    className="focus-ring grid h-7 w-7 place-items-center rounded-md text-muted-foreground hover:bg-muted"
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                ) : null
              }
            >
              {entity ? `Evidence for ${text(entity.name, "entity")}` : "Related Evidence"}
            </SectionLabel>

            {!entity ? (
              <p className="px-4 py-12 text-center text-sm text-muted-foreground">
                Select an entity to inspect its linked evidence records.
              </p>
            ) : related.length === 0 ? (
              <p className="px-4 py-12 text-center text-sm text-muted-foreground">
                No evidence records matched this entity's record IDs.
              </p>
            ) : (
              <ol className="space-y-5 p-4">
                {related.map((record) => (
                  <TimelineItem key={record.id} record={record} />
                ))}
              </ol>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
