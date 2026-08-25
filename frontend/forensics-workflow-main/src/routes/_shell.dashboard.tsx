import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { HardDrive, Files, Users, ShieldAlert, ArrowRight, Clock, FolderGit2, Loader2, AlertTriangle, Smartphone, UserCheck } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatCard } from "@/components/forensics/StatCard";
import { SummaryPanel } from "@/components/forensics/SummaryPanel";
import { Panel, SectionLabel, KindBadge, RecordId } from "@/components/forensics/primitives";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { useReport } from "@/lib/use-report";
import { useInvestigation } from "@/lib/investigation";
import { formatTimestamp, text } from "@/lib/report-types";
import { getCases, getDevices, getContacts, type CaseRecord, type DeviceRecord, type ContactRecord } from "@/services/forensics-api";

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
  const { activeCaseId, selectCase } = useInvestigation();
  const report = useReport();
  const recent = report.timeline.slice(-5).reverse();
  const quickLinks = NAV_ITEMS.filter((i) =>
    ["/timeline", "/entities", "/flags", "/media"].includes(i.to),
  );

  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loadingCases, setLoadingCases] = useState<boolean>(true);
  const [casesError, setCasesError] = useState<string | null>(null);

  const [devices, setDevices] = useState<DeviceRecord[]>([]);
  const [contacts, setContacts] = useState<ContactRecord[]>([]);
  const [loadingDevices, setLoadingDevices] = useState<boolean>(false);
  const [loadingContacts, setLoadingContacts] = useState<boolean>(false);
  const [devicesError, setDevicesError] = useState<string | null>(null);
  const [contactsError, setContactsError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    getCases()
      .then((data) => {
        if (mounted) {
          setCases(data);
          setLoadingCases(false);
          // If no active case selected, select the first available case
          if (data.length > 0 && activeCaseId === null) {
            selectCase(data[0].id);
          }
        }
      })
      .catch((err) => {
        if (mounted) {
          setCasesError(err instanceof Error ? err.message : "Failed to load cases from backend.");
          setLoadingCases(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (activeCaseId === null) return;
    let mounted = true;

    setLoadingDevices(true);
    setDevicesError(null);
    getDevices(activeCaseId)
      .then((data) => {
        if (mounted) {
          setDevices(data);
          setLoadingDevices(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setDevicesError(err instanceof Error ? err.message : "Failed to load device information.");
          setLoadingDevices(false);
        }
      });

    setLoadingContacts(true);
    setContactsError(null);
    getContacts(activeCaseId)
      .then((data) => {
        if (mounted) {
          setContacts(data);
          setLoadingContacts(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setContactsError(err instanceof Error ? err.message : "Failed to load contacts.");
          setLoadingContacts(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [activeCaseId]);

  const activeDevice = devices.length > 0 ? devices[0] : null;

  return (
    <>
      <PageHeader
        title="Case Dashboard"
        description="Overview of the extracted evidence set and derived analysis."
      />

      {/* Real PostgreSQL Cases Section */}
      <div className="mb-5">
        <Panel>
          <SectionLabel
            icon={<FolderGit2 className="h-4 w-4 text-brand-deep" aria-hidden />}
            right={
              <span className="text-xs font-medium text-muted-foreground">
                Click a case to switch active investigation
              </span>
            }
          >
            PostgreSQL Database Cases
          </SectionLabel>

          {loadingCases && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Loading real database cases from FastAPI...
            </div>
          )}

          {casesError && (
            <div className="flex items-center gap-2 border-l-4 border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{casesError}</span>
            </div>
          )}

          {!loadingCases && !casesError && cases.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">
              No cases found in PostgreSQL database. Upload a UFDR package to get started.
            </p>
          )}

          {!loadingCases && !casesError && cases.length > 0 && (
            <div className="divide-y divide-border">
              {cases.map((c) => {
                const isActive = c.id === activeCaseId;
                return (
                  <div
                    key={c.id}
                    onClick={() => selectCase(c.id)}
                    className={`flex cursor-pointer flex-wrap items-center justify-between gap-3 p-4 transition-colors hover:bg-muted/50 ${
                      isActive ? "bg-ai/80 border-l-4 border-brand-deep" : ""
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded px-2 py-0.5 font-mono text-xs font-bold ${
                            isActive
                              ? "bg-brand-deep text-primary-foreground"
                              : "bg-brand-deep/10 text-brand-deep"
                          }`}
                        >
                          CASE #{c.id}
                        </span>
                        <h4 className="text-sm font-semibold text-foreground">{c.case_name}</h4>
                        {isActive && (
                          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      {c.source_file && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Source: <code className="rounded bg-muted px-1.5 py-0.5">{c.source_file}</code>
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className="block font-mono text-xs text-muted-foreground">
                        Created: {formatTimestamp(c.created_at)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Panel>
      </div>

      {/* Case Overview Stat Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={<HardDrive className="h-4 w-4" aria-hidden />}
          label="Device ID"
          value={loadingDevices ? "..." : activeDevice ? activeDevice.device_id : "No Device"}
          hint={activeDevice?.imei ? `IMEI: ${activeDevice.imei}` : "Acquired device"}
        />
        <StatCard
          icon={<Files className="h-4 w-4" aria-hidden />}
          label="Evidence"
          value={String(report.timeline.length)}
          hint="Extracted records"
        />
        <StatCard
          icon={<Users className="h-4 w-4" aria-hidden />}
          label="Contacts"
          value={loadingContacts ? "..." : String(contacts.length)}
          hint="Extracted contacts"
        />
        <StatCard
          icon={<ShieldAlert className="h-4 w-4" aria-hidden />}
          label="Flags"
          value={String(report.flags.length)}
          hint="Analysis-derived"
        />
      </div>

      {/* Real Extracted Device & Contacts Cards for Selected Case */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Device Information Panel */}
        <Panel>
          <SectionLabel icon={<Smartphone className="h-4 w-4 text-brand-deep" aria-hidden />}>
            Active Device Details (Case #{activeCaseId ?? "-"})
          </SectionLabel>

          {loadingDevices && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Loading device information from PostgreSQL...
            </div>
          )}

          {devicesError && (
            <div className="flex items-center gap-2 border-l-4 border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{devicesError}</span>
            </div>
          )}

          {!loadingDevices && !devicesError && devices.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">
              No device record found for Case #{activeCaseId}.
            </p>
          )}

          {!loadingDevices && !devicesError && devices.length > 0 && (
            <div className="divide-y divide-border p-4 space-y-3">
              {devices.map((d) => (
                <div key={d.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase text-muted-foreground">
                      Device ID
                    </span>
                    <span className="font-mono text-sm font-bold text-foreground">{d.device_id}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase text-muted-foreground">
                      IMEI
                    </span>
                    <span className="font-mono text-sm text-foreground">{d.imei || "N/A"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase text-muted-foreground">
                      Extraction Date
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {formatTimestamp(d.extraction_date)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* Contacts Panel */}
        <Panel>
          <SectionLabel icon={<UserCheck className="h-4 w-4 text-brand-deep" aria-hidden />}>
            Extracted Contacts ({contacts.length} Found)
          </SectionLabel>

          {loadingContacts && (
            <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-brand-deep" />
              Loading extracted contacts...
            </div>
          )}

          {contactsError && (
            <div className="flex items-center gap-2 border-l-4 border-destructive bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{contactsError}</span>
            </div>
          )}

          {!loadingContacts && !contactsError && contacts.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">
              No contacts extracted for Case #{activeCaseId}.
            </p>
          )}

          {!loadingContacts && !contactsError && contacts.length > 0 && (
            <div className="max-h-[220px] overflow-y-auto divide-y divide-border">
              {contacts.map((c) => (
                <div key={c.id} className="flex items-center justify-between px-4 py-2.5">
                  <div>
                    <span className="text-sm font-semibold text-foreground">
                      {c.name || c.contact_id}
                    </span>
                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                      ({c.contact_id})
                    </span>
                  </div>
                  <span className="font-mono text-xs text-brand-deep">{c.phone || "No Phone"}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
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

