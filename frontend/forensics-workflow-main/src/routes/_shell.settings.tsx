import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { UserRound, Palette, FileText, Info, LogOut } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Panel, SectionLabel } from "@/components/forensics/primitives";
import { useAuth } from "@/lib/auth";
import { useReport } from "@/lib/use-report";
import { cn } from "@/lib/utils";

const title = "Settings — Evidence Examiner Desk";
const description =
  "Account information, appearance, report preferences and application details for the Evidence Examiner Desk platform.";

export const Route = createFileRoute("/_shell/settings")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: SettingsPage,
});

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3">
      <span className="min-w-0 truncate text-sm text-muted-foreground">{label}</span>
      <span className="truncate text-sm font-semibold text-foreground">{value}</span>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3">
      <span className="min-w-0 text-sm text-muted-foreground">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={cn(
          "focus-ring relative h-6 w-11 shrink-0 rounded-full transition-colors",
          checked ? "bg-brand-deep" : "bg-muted",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-card shadow-card transition-all",
            checked ? "left-[22px]" : "left-0.5",
          )}
        />
      </button>
    </div>
  );
}

function SettingsPage() {
  const { user, logout } = useAuth();
  const report = useReport();
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");
  const [includeAi, setIncludeAi] = useState(true);
  const [includeMedia, setIncludeMedia] = useState(true);
  const [monospaceIds, setMonospaceIds] = useState(true);

  return (
    <>
      <PageHeader title="Settings" description="Account, appearance and report preferences." />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel>
          <SectionLabel icon={<UserRound className="h-4 w-4 text-brand-deep" aria-hidden />}>
            Account
          </SectionLabel>
          <div className="divide-y divide-border">
            <Row label="Name" value={user?.name ?? "—"} />
            <Row label="Email / username" value={user?.email ?? "—"} />
            <Row label="Role" value={user?.role ?? "Forensic Examiner"} />
            <Row label="Active case device" value={report.device_id} />
          </div>
        </Panel>

        <Panel>
          <SectionLabel icon={<Palette className="h-4 w-4 text-brand-deep" aria-hidden />}>
            Appearance
          </SectionLabel>
          <div className="divide-y divide-border">
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3">
              <span className="min-w-0 text-sm text-muted-foreground">Layout density</span>
              <div className="inline-flex rounded-lg border border-border p-1">
                {(["comfortable", "compact"] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDensity(d)}
                    aria-pressed={density === d}
                    className={cn(
                      "focus-ring rounded-md px-3 py-1 text-xs font-semibold capitalize transition-colors",
                      density === d
                        ? "bg-brand-deep text-primary-foreground"
                        : "text-muted-foreground hover:bg-ai hover:text-brand-dark",
                    )}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
            <Toggle label="Monospace record identifiers" checked={monospaceIds} onChange={setMonospaceIds} />
            <Row label="Theme" value="Forensic Red / White" />
          </div>
        </Panel>

        <Panel>
          <SectionLabel icon={<FileText className="h-4 w-4 text-brand-deep" aria-hidden />}>
            Report Preferences
          </SectionLabel>
          <div className="divide-y divide-border">
            <Toggle
              label="Include AI-derived analysis in exports"
              checked={includeAi}
              onChange={setIncludeAi}
            />
            <Toggle label="Include media previews" checked={includeMedia} onChange={setIncludeMedia} />
            <Row label="Export format" value="PDF (planned)" />
          </div>
        </Panel>

        <Panel>
          <SectionLabel icon={<Info className="h-4 w-4 text-brand-deep" aria-hidden />}>
            Application
          </SectionLabel>
          <div className="divide-y divide-border">
            <Row label="Application" value="Evidence Examiner Desk" />
            <Row label="Version" value="1.0.0" />
            <Row label="Data source" value="report_data.json (mock)" />
            <Row label="Authentication" value="Local (frontend only)" />
          </div>
          <div className="border-t border-border p-4">
            <button
              type="button"
              onClick={logout}
              className="focus-ring inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-deep text-sm font-semibold text-primary-foreground transition-colors hover:bg-brand-dark"
            >
              <LogOut className="h-4 w-4" aria-hidden />
              Logout
            </button>
          </div>
        </Panel>
      </div>
    </>
  );
}
