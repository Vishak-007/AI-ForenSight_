import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

const title = "Evidence Examiner Desk — Digital Forensics Investigation Platform";
const description =
  "Investigate device evidence with a chronological timeline, entity correlation, analysis flags, media inspection and clearly labelled AI-derived findings.";

export const Route = createFileRoute("/")({
  ssr: false,
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: Index,
});

function Index() {
  const { user, hydrated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!hydrated) return;
    navigate({ to: user ? "/dashboard" : "/login", replace: true });
  }, [hydrated, user, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <p className="label-caps text-muted-foreground">Opening Evidence Examiner Desk…</p>
    </div>
  );
}
