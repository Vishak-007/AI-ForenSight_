import { createFileRoute, Link } from "@tanstack/react-router";
import { HardDrive, Files, Users, ShieldAlert, ArrowRight, Clock } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatCard } from "@/components/forensics/StatCard";
import { SummaryPanel } from "@/components/forensics/SummaryPanel";
import { Panel, SectionLabel, KindBadge, RecordId } from "@/components/forensics/primitives";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { useReport } from "@/lib/use-report";
import { formatTimestamp, text } from "@/lib/report-types";

const title = "Case Dashboard — Evidence Examiner Desk";
const description =
  "High-level forensic case overview: device information, evidence statistics, entities, analysis flags and the AI-generated case summary.";

export const Route = createFileRoute("/_shell/dashboard")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const report = useReport();
  const recent = report.timeline.slice(-5).reverse();
  const quickLinks = NAV_ITEMS.filter((i) =>
    ["/timeline", "/entities", "/flags", "/media"].includes(i.to),
  );

  return (
    <>
      <PageHeader
        title="Case Dashboard"
        description="Overview of the extracted evidence set and derived analysis."
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={<HardDrive className="h-4 w-4" aria-hidden />}
          label="Device ID"
          value={report.device_id}
          hint="Acquired device"
        />
        <StatCard
          icon={<Files className="h-4 w-4" aria-hidden />}
          label="Evidence"
          value={String(report.timeline.length)}
          hint="Extracted records"
        />
        <StatCard
          icon={<Users className="h-4 w-4" aria-hidden />}
          label="Entities"
          value={String(report.entities.length)}
          hint="Correlated identifiers"
        />
        <StatCard
          icon={<ShieldAlert className="h-4 w-4" aria-hidden />}
          label="Flags"
          value={String(report.flags.length)}
          hint="Analysis-derived"
        />
      </div>

      <div className="mt-5">
        <SummaryPanel summary={report.overall_summary} />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Panel>
          <SectionLabel
            icon={<Clock className="h-4 w-4 text-brand-deep" aria-hidden />}
            right={
              <Link
                to="/timeline"
                className="focus-ring rounded text-xs font-semibold text-brand-deep hover:text-brand-dark"
              >
                View timeline
              </Link>
            }
          >
            Recent Evidence
          </SectionLabel>
          {recent.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-muted-foreground">
              No evidence records in this report.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {recent.map((record) => (
                <li key={record.id} className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <KindBadge kind={text(record.kind, "record")} />
                    <RecordId id={record.id} />
                    <span className="ml-auto font-mono text-xs text-muted-foreground">
                      {formatTimestamp(record.timestamp)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-semibold leading-snug text-foreground">
                    {text(record.headline, "Untitled record")}
                  </p>
                  {text(record.detail) && (
                    <p className="mt-0.5 line-clamp-2 text-sm text-muted-foreground">
                      {text(record.detail)}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div className="space-y-3">
          {quickLinks.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="focus-ring group flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-card transition-colors hover:border-brand-accent hover:bg-ai"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ai text-brand-deep group-hover:bg-brand-deep group-hover:text-primary-foreground">
                <item.icon className="h-4 w-4" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-foreground">{item.label}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {item.description}
                </span>
              </span>
              <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
