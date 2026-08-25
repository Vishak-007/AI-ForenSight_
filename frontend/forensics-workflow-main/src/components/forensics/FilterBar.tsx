import type { Entity } from "@/lib/report-types";
import { list, text } from "@/lib/report-types";
import { cn } from "@/lib/utils";

const KINDS = [
  { value: "message", label: "Messages" },
  { value: "call", label: "Calls" },
  { value: "audio", label: "Audio" },
  { value: "image", label: "Images" },
];

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "focus-ring inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors",
        active
          ? "border-brand-deep bg-brand-deep text-primary-foreground"
          : "border-border bg-card text-muted-foreground hover:border-brand-accent hover:bg-ai hover:text-brand-dark",
      )}
    >
      {children}
    </button>
  );
}

export function FilterBar({
  entities,
  activeEntity,
  onEntityChange,
  activeKind,
  onKindChange,
}: {
  entities: Entity[];
  activeEntity: number | null;
  onEntityChange: (index: number | null) => void;
  activeKind: string | null;
  onKindChange: (kind: string | null) => void;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-3 shadow-card sm:p-4">
      <div className="space-y-3">
        <div>
          <p className="label-caps text-muted-foreground">Evidence type</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {KINDS.map((k) => (
              <Chip
                key={k.value}
                active={activeKind === k.value}
                onClick={() => onKindChange(activeKind === k.value ? null : k.value)}
              >
                {k.label}
              </Chip>
            ))}
          </div>
        </div>

        {entities.length > 0 && (
          <div>
            <p className="label-caps text-muted-foreground">Entity</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {entities.map((entity, index) => (
                <Chip
                  key={`${text(entity.name, "entity")}-${index}`}
                  active={activeEntity === index}
                  onClick={() => onEntityChange(activeEntity === index ? null : index)}
                >
                  {text(entity.name, "Unnamed")}
                  <span className="font-mono opacity-70">{list(entity.record_ids).length}</span>
                </Chip>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
