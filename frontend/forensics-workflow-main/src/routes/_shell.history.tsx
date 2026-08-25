import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  RefreshCw,
  Fingerprint,
  FileCheck,
  User,
  Clock,
  Database,
  Lock,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Panel } from "@/components/forensics/primitives";
import { useInvestigation } from "@/lib/investigation";
import {
  getAuditLogs,
  verifyAuditTrail,
  type AuditLogRecord,
  type AuditVerificationResult,
} from "@/services/forensics-api";

const title = "Audit Trail & Forensic History — AI-ForenSight";
const description =
  "Cryptographically verified chain-of-custody audit trail tracking all evidence extractions, access events, and investigative actions.";

export const Route = createFileRoute("/_shell/history")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: AuditHistoryPage,
});

function getActionBadgeStyle(action: string): { bg: string; text: string; border: string } {
  if (action.includes("UPLOAD") || action.includes("SUCCESS")) {
    return { bg: "bg-emerald-950/40", text: "text-emerald-400", border: "border-emerald-800/50" };
  }
  if (action.includes("FAILED") || action.includes("ERROR")) {
    return { bg: "bg-rose-950/40", text: "text-rose-400", border: "border-rose-800/50" };
  }
  if (action.includes("VIEW") || action.includes("LIST")) {
    return { bg: "bg-sky-950/40", text: "text-sky-400", border: "border-sky-800/50" };
  }
  return { bg: "bg-amber-950/40", text: "text-amber-400", border: "border-amber-800/50" };
}

function formatUtcTimestamp(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return isoStr;
  }
}

function AuditHistoryPage() {
  const { activeCaseId } = useInvestigation();

  const [logs, setLogs] = useState<AuditLogRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Verification state
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<AuditVerificationResult | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedAction, setSelectedAction] = useState<string>("ALL");
  const [filterByActiveCase, setFilterByActiveCase] = useState<boolean>(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAuditLogs({
        caseId: filterByActiveCase && activeCaseId ? activeCaseId : null,
        limit: 200,
      });
      setLogs(res.logs);
    } catch (err: any) {
      setError(err?.message || "Failed to load audit history.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await verifyAuditTrail();
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({
        status: "corrupted",
        total_entries: 0,
        message: err?.message || "Verification request failed.",
      });
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [filterByActiveCase, activeCaseId]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const availableActions = useMemo(() => {
    const set = new Set<string>();
    logs.forEach((l: AuditLogRecord) => set.add(l.action));
    return Array.from(set).sort();
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter((log: AuditLogRecord) => {
      if (selectedAction !== "ALL" && log.action !== selectedAction) return false;
      if (!searchQuery.trim()) return true;

      const q = searchQuery.toLowerCase();
      const matchAction = log.action.toLowerCase().includes(q);
      const matchUser = log.user_id.toLowerCase().includes(q);
      const matchResource =
        (log.resource_type ? log.resource_type.toLowerCase().includes(q) : false) ||
        (log.resource_id ? log.resource_id.toLowerCase().includes(q) : false);
      const matchIp = log.ip_address ? log.ip_address.toLowerCase().includes(q) : false;
      const matchHash = log.entry_hash ? log.entry_hash.toLowerCase().includes(q) : false;

      let matchDetails = false;
      if (typeof log.details === "object" && log.details !== null) {
        matchDetails = JSON.stringify(log.details).toLowerCase().includes(q);
      } else if (typeof log.details === "string") {
        matchDetails = log.details.toLowerCase().includes(q);
      }

      return matchAction || matchUser || matchResource || matchIp || matchHash || matchDetails;
    });
  }, [logs, selectedAction, searchQuery]);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Audit Trail & Chain of Custody"
        description="Cryptographically verified immutable event ledger. Tracks all evidence access, parsing, and pipeline operations."
        actions={
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-emerald-300 bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-700/50 rounded-lg shadow-sm transition-colors disabled:opacity-50"
          >
            <ShieldCheck className={`w-4 h-4 ${verifying ? "animate-spin" : ""}`} />
            {verifying ? "Verifying SHA-256 Chain…" : "Verify Cryptographic Chain"}
          </button>
        }
      />

      {/* Cryptographic Verification Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
            verificationResult.status === "verified" || verificationResult.status === "valid"
              ? "bg-emerald-950/30 border-emerald-700/60 text-emerald-200"
              : "bg-rose-950/30 border-rose-700/60 text-rose-200"
          }`}
        >
          {verificationResult.status === "verified" || verificationResult.status === "valid" ? (
            <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
          )}
          <div className="flex-1 space-y-1">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-sm">
                {verificationResult.status === "verified" || verificationResult.status === "valid"
                  ? "Chain-of-Custody Verified Intact"
                  : "Cryptographic Tamper Alert"}
              </h4>
              <span className="text-xs px-2 py-0.5 rounded bg-black/40 font-mono">
                {verificationResult.total_entries} Blocks Verified
              </span>
            </div>
            <p className="text-xs opacity-90">{verificationResult.message}</p>
            {verificationResult.corrupted_at_id && (
              <p className="text-xs font-mono text-rose-300">
                Corruption detected at Record ID: #{verificationResult.corrupted_at_id} — {verificationResult.reason}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Panel className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase font-medium">Logged Actions</p>
            <p className="text-xl font-bold text-foreground">{logs.length}</p>
          </div>
        </Panel>

        <Panel className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Fingerprint className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase font-medium">Chain Integrity</p>
            <p className="text-xl font-bold text-emerald-400">SHA-256 Chained</p>
          </div>
        </Panel>

        <Panel className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <User className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase font-medium">Distinct Actors</p>
            <p className="text-xl font-bold text-foreground">
              {new Set(logs.map((l: AuditLogRecord) => l.user_id)).size}
            </p>
          </div>
        </Panel>

        <Panel className="p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase font-medium">Immutability</p>
            <p className="text-xl font-bold text-foreground">Append-Only</p>
          </div>
        </Panel>
      </div>

      {/* Control Bar: Filters & Search */}
      <Panel className="p-4 space-y-4">
        <div className="flex flex-col md:flex-row items-center gap-3 justify-between">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by action, user ID, IP, resource or SHA-256 hash…"
              value={searchQuery}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary text-foreground placeholder:text-muted-foreground"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <select
              value={selectedAction}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedAction(e.target.value)}
              className="bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="ALL">All Event Types ({availableActions.length})</option>
              {availableActions.map((act: string) => (
                <option key={act} value={act}>
                  {act}
                </option>
              ))}
            </select>

            {activeCaseId && (
              <button
                onClick={() => setFilterByActiveCase(!filterByActiveCase)}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  filterByActiveCase
                    ? "bg-primary/20 text-primary border-primary/40"
                    : "bg-background text-muted-foreground border-border hover:text-foreground"
                }`}
              >
                Case #{activeCaseId} Only
              </button>
            )}

            <button
              onClick={fetchLogs}
              disabled={loading}
              title="Refresh logs"
              className="p-2 border border-border rounded-lg hover:bg-muted/40 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
      </Panel>

      {/* Audit Log Stream Table */}
      <Panel className="overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 animate-spin text-primary" />
            <p className="text-sm">Loading cryptographic audit trail…</p>
          </div>
        ) : error ? (
          <div className="p-12 text-center text-rose-400 space-y-2">
            <ShieldAlert className="w-8 h-8 mx-auto" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground space-y-2">
            <FileCheck className="w-8 h-8 mx-auto opacity-40" />
            <p className="text-sm">No audit records match the selected filters.</p>
          </div>
        ) : (
          <div className="divide-y divide-border/60">
            <div className="grid grid-cols-12 gap-3 px-4 py-3 bg-muted/30 text-xs font-semibold text-muted-foreground uppercase">
              <div className="col-span-1">ID</div>
              <div className="col-span-3">Timestamp (UTC)</div>
              <div className="col-span-3">Action Event</div>
              <div className="col-span-2">User / Actor</div>
              <div className="col-span-2">Resource</div>
              <div className="col-span-1 text-right">Details</div>
            </div>

            {filteredLogs.map((log: AuditLogRecord) => {
              const isExpanded = expandedRow === log.id;
              const badge = getActionBadgeStyle(log.action);

              return (
                <div key={log.id} className="transition-colors hover:bg-muted/10">
                  <div
                    onClick={() => setExpandedRow(isExpanded ? null : log.id)}
                    className="grid grid-cols-12 gap-3 px-4 py-3.5 items-center text-sm cursor-pointer"
                  >
                    {/* Log ID */}
                    <div className="col-span-1 font-mono text-xs text-muted-foreground">
                      #{log.id}
                    </div>

                    {/* Timestamp */}
                    <div className="col-span-3 flex items-center gap-2 text-xs text-foreground/90 font-mono">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      {formatUtcTimestamp(log.timestamp)}
                    </div>

                    {/* Action Badge */}
                    <div className="col-span-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono font-medium border ${badge.bg} ${badge.text} ${badge.border}`}
                      >
                        {log.action}
                      </span>
                    </div>

                    {/* User / Actor */}
                    <div className="col-span-2 text-xs text-foreground/80 flex items-center gap-1.5 truncate">
                      <User className="w-3 h-3 text-muted-foreground shrink-0" />
                      <span className="truncate">{log.user_id}</span>
                    </div>

                    {/* Resource */}
                    <div className="col-span-2 text-xs text-muted-foreground truncate font-mono">
                      {log.resource_type ? (
                        <span>
                          {log.resource_type}
                          {log.resource_id ? ` #${log.resource_id}` : ""}
                        </span>
                      ) : log.case_id ? (
                        <span>Case #{log.case_id}</span>
                      ) : (
                        "—"
                      )}
                    </div>

                    {/* Expand Arrow */}
                    <div className="col-span-1 flex justify-end text-muted-foreground">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Cryptographic & Detail Inspector */}
                  {isExpanded && (
                    <div className="px-6 py-4 bg-muted/20 border-t border-border/40 space-y-4 text-xs font-mono">
                      {/* Cryptographic Hash Chaining Block */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-black/40 p-3 rounded-lg border border-border/50">
                        <div className="space-y-1">
                          <span className="text-[11px] text-muted-foreground uppercase flex items-center gap-1.5 font-sans font-semibold">
                            <Fingerprint className="w-3.5 h-3.5 text-muted-foreground" />
                            Previous Block Hash (Parent):
                          </span>
                          <div className="flex items-center justify-between gap-2 bg-background/50 px-2 py-1.5 rounded border border-border/40">
                            <span className="truncate text-muted-foreground">{log.prev_log_hash}</span>
                            <button
                              onClick={() => copyToClipboard(log.prev_log_hash, `prev-${log.id}`)}
                              className="text-muted-foreground hover:text-foreground shrink-0"
                            >
                              {copiedHash === `prev-${log.id}` ? (
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>

                        <div className="space-y-1">
                          <span className="text-[11px] text-emerald-400 uppercase flex items-center gap-1.5 font-sans font-semibold">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                            Entry SHA-256 Hash:
                          </span>
                          <div className="flex items-center justify-between gap-2 bg-emerald-950/20 px-2 py-1.5 rounded border border-emerald-800/40">
                            <span className="truncate text-emerald-300 font-semibold">{log.entry_hash}</span>
                            <button
                              onClick={() => copyToClipboard(log.entry_hash, `curr-${log.id}`)}
                              className="text-emerald-400 hover:text-emerald-300 shrink-0"
                            >
                              {copiedHash === `curr-${log.id}` ? (
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Network & Client Context */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-sans">
                        <div>
                          <span className="text-muted-foreground text-xs">Client IP Address:</span>
                          <p className="font-mono text-foreground">{log.ip_address || "Localhost / Internal"}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Case Reference:</span>
                          <p className="font-mono text-foreground">
                            {log.case_id ? `Case ID #${log.case_id}` : "Global System Event"}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground text-xs">Client User-Agent:</span>
                          <p className="truncate text-foreground" title={log.user_agent || "N/A"}>
                            {log.user_agent || "N/A"}
                          </p>
                        </div>
                      </div>

                      {/* Structured Event Details */}
                      {log.details && (
                        <div className="space-y-1">
                          <span className="text-muted-foreground text-xs font-sans">Payload & Event Context:</span>
                          <pre className="p-3 bg-black/60 rounded-lg text-emerald-300/90 text-xs overflow-x-auto border border-border/40">
                            {typeof log.details === "object"
                              ? JSON.stringify(log.details, null, 2)
                              : log.details}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
