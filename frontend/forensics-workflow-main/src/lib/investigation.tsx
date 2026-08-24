import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  ForensicsApiError,
  STAGE_DEFS,
  getAnalysisStatus,
  getReportData,
  startAnalysis,
  uploadUFDR,
} from "@/services/forensics-api";
import type { AnalysisStage, AnalysisState, UploadResult } from "@/services/forensics-api";
import type { ReportData } from "@/lib/report-types";

const STORAGE_KEY = "eed.investigation";

export interface InvestigationState {
  /** Uploaded case file metadata, null before any upload. */
  upload: UploadResult | null;
  uploadProgress: number;
  uploading: boolean;
  analysisId: string | null;
  analysisState: AnalysisState;
  progress: number;
  stages: AnalysisStage[];
  statusMessage: string;
  error: string | null;
  /** report_data.json assembled by the backend, null until analysis completes. */
  reportData: ReportData | null;
  startedAt: string | null;
  completedAt: string | null;
}

interface InvestigationApi extends InvestigationState {
  uploadFile: (file: File) => Promise<void>;
  clearFile: () => void;
  beginAnalysis: () => Promise<void>;
  reset: () => void;
  clearError: () => void;
}

const pendingStages = (): AnalysisStage[] =>
  STAGE_DEFS.map((s) => ({ ...s, state: "pending" as const }));

const initialState: InvestigationState = {
  upload: null,
  uploadProgress: 0,
  uploading: false,
  analysisId: null,
  analysisState: "idle",
  progress: 0,
  stages: pendingStages(),
  statusMessage: "",
  error: null,
  reportData: null,
  startedAt: null,
  completedAt: null,
};

const InvestigationContext = createContext<InvestigationApi | null>(null);

const message = (err: unknown, fallback: string) =>
  err instanceof ForensicsApiError ? err.message : fallback;

export function InvestigationProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<InvestigationState>(initialState);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const uploadRef = useRef<UploadResult | null>(null);

  /* restore the current investigation so navigation never loses case state */
  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as Partial<InvestigationState>;
        setState((prev) => ({
          ...prev,
          ...saved,
          uploading: false,
          // a reload cannot resume an in-flight pipeline
          analysisState: saved.analysisState === "running" ? "idle" : (saved.analysisState ?? "idle"),
          stages: saved.stages?.length ? saved.stages : pendingStages(),
        }));
      }
    } catch {
      /* ignore corrupt state */
    }
  }, []);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          upload: state.upload,
          analysisId: state.analysisId,
          analysisState: state.analysisState,
          progress: state.progress,
          stages: state.stages,
          reportData: state.reportData,
          startedAt: state.startedAt,
          completedAt: state.completedAt,
        }),
      );
    } catch {
      /* storage full / unavailable — state simply is not persisted */
    }
  }, [state]);

  useEffect(() => {
    uploadRef.current = state.upload;
  }, [state.upload]);

  const stopPolling = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const uploadFile = useCallback(async (file: File) => {
    setState((s) => ({ ...s, uploading: true, uploadProgress: 0, error: null }));
    try {
      const result = await uploadUFDR(file, (p) =>
        setState((s) => ({ ...s, uploadProgress: p })),
      );
      setState({
        ...initialState,
        upload: result,
        uploadProgress: 100,
        uploading: false,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        uploading: false,
        uploadProgress: 0,
        upload: null,
        error: message(err, "The file could not be uploaded. Please try again."),
      }));
    }
  }, []);

  const clearFile = useCallback(() => {
    stopPolling();
    setState({ ...initialState });
  }, [stopPolling]);

  const reset = clearFile;

  const clearError = useCallback(() => setState((s) => ({ ...s, error: null })), []);

  const beginAnalysis = useCallback(async () => {
    const caseId = uploadRef.current?.caseId ?? null;
    if (!caseId) {
      setState((s) => ({ ...s, error: "Upload a UFDR case file before starting analysis." }));
      return;
    }
    stopPolling();
    setState((s) => ({
      ...s,
      error: null,
      analysisState: "running",
      progress: 0,
      stages: pendingStages(),
      statusMessage: "Analysis is running…",
      startedAt: new Date().toISOString(),
      reportData: null,
      completedAt: null,
    }));

    try {
      const { analysisId } = await startAnalysis(caseId);
      setState((s) => ({ ...s, analysisId }));

      timer.current = setInterval(async () => {
        try {
          const status = await getAnalysisStatus(analysisId);
          setState((s) => ({
            ...s,
            progress: status.progress,
            stages: status.stages,
            statusMessage: status.message,
          }));
          if (status.state === "completed") {
            stopPolling();
            const data = await getReportData(caseId);
            setState((s) => ({
              ...s,
              analysisState: "completed",
              progress: 100,
              statusMessage: "Analysis complete.",
              reportData: data,
              completedAt: new Date().toISOString(),
            }));
          }
        } catch (err) {
          stopPolling();
          setState((s) => ({
            ...s,
            analysisState: "failed",
            stages: s.stages.map((st) =>
              st.state === "processing" ? { ...st, state: "failed" } : st,
            ),
            error: message(
              err,
              "The forensic analysis could not be completed. Please review the analysis status and try again.",
            ),
          }));
        }
      }, 600);
    } catch (err) {
      stopPolling();
      setState((s) => ({
        ...s,
        analysisState: "failed",
        error: message(
          err,
          "The analysis service is unavailable. Please try again in a moment.",
        ),
      }));
    }
  }, [stopPolling]);

  const value = useMemo<InvestigationApi>(
    () => ({ ...state, uploadFile, clearFile, beginAnalysis, reset, clearError }),
    [state, uploadFile, clearFile, beginAnalysis, reset, clearError],
  );

  return <InvestigationContext.Provider value={value}>{children}</InvestigationContext.Provider>;
}

export function useInvestigation(): InvestigationApi {
  const ctx = useContext(InvestigationContext);
  if (!ctx) throw new Error("useInvestigation must be used within InvestigationProvider");
  return ctx;
}

/** Non-throwing accessor for modules that may render outside the provider. */
export function useInvestigationOptional(): InvestigationApi | null {
  return useContext(InvestigationContext);
}
