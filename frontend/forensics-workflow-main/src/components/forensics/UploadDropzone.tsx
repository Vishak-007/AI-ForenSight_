import { useRef, useState } from "react";
import { UploadCloud, FileWarning } from "lucide-react";
import { isValidUfdrFile } from "@/services/forensics-api";
import { cn } from "@/lib/utils";

export function UploadDropzone({
  onFile,
  disabled,
}: {
  onFile: (file: File) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handle = (file: File | undefined) => {
    if (!file) return;
    if (!isValidUfdrFile(file)) {
      setLocalError("Invalid file — please upload a valid UFDR file (.ufdr).");
      return;
    }
    setLocalError(null);
    onFile(file);
  };

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Drop UFDR file here or browse files"
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) handle(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          "focus-ring grid cursor-pointer place-items-center rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors sm:py-14",
          dragging
            ? "border-brand-accent bg-ai"
            : "border-ai-border bg-card hover:border-brand-accent hover:bg-ai/60",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <span className="grid h-14 w-14 place-items-center rounded-full bg-brand-deep shadow-red">
          <UploadCloud className="h-7 w-7 text-primary-foreground" aria-hidden />
        </span>
        <span className="label-caps mt-4 block text-foreground">Drop UFDR file here</span>
        <span className="mt-1 block text-sm text-muted-foreground">or click Browse Files</span>
        <span className="mt-3 inline-flex items-center rounded-md border border-border bg-muted px-2 py-1 font-mono text-[11px] text-muted-foreground">
          Supported format: .UFDR
        </span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".ufdr"
        className="hidden"
        onChange={(e) => {
          handle(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {localError && (
        <p
          role="alert"
          className="mt-3 flex items-start gap-2 rounded-lg border border-ai-border bg-ai px-3 py-2 text-sm font-semibold text-brand-dark"
        >
          <FileWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {localError}
        </p>
      )}
    </div>
  );
}
