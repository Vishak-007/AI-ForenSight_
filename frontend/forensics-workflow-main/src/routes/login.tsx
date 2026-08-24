import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Fingerprint, Eye, EyeOff, Lock, Mail, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";

const title = "Sign In — Evidence Examiner Desk";
const description =
  "Secure sign-in for the Evidence Examiner Desk digital forensics investigation platform.";

export const Route = createFileRoute("/login")({
  ssr: false,
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { user, hydrated, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({});
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (hydrated && user) navigate({ to: "/dashboard", replace: true });
  }, [hydrated, user, navigate]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const next: typeof errors = {};
    if (!email.trim()) next.email = "Email or username is required.";
    else if (email.includes("@") && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setPending(true);
    try {
      await login(email.trim(), password, remember);
      navigate({ to: "/dashboard", replace: true });
    } catch (err) {
      setErrors({ form: err instanceof Error ? err.message : "Unable to sign in." });
    } finally {
      setPending(false);
    }
  };

  const fieldClass = (invalid?: string) =>
    `focus-ring h-12 w-full rounded-lg border bg-background pl-11 pr-11 text-sm text-foreground placeholder:text-muted-foreground ${
      invalid ? "border-brand-accent" : "border-input focus:border-brand-accent"
    }`;

  return (
    <div className="grid min-h-screen grid-cols-1 bg-background lg:grid-cols-2">
      <section className="relative hidden flex-col justify-between bg-brand-dark p-10 text-primary-foreground lg:flex">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-accent">
            <Fingerprint className="h-6 w-6" aria-hidden />
          </span>
          <span>
            <span className="block text-base font-bold tracking-tight">Evidence Examiner Desk</span>
            <span className="label-caps block opacity-80">Digital Forensics</span>
          </span>
        </div>

        <div className="max-w-md">
          <h2 className="text-3xl font-bold leading-tight">
            Digital Forensics Investigation Platform
          </h2>
          <p className="mt-4 text-sm leading-relaxed opacity-85">
            Examine extracted device evidence — messages, calls, audio, imagery, OCR and
            transcripts — alongside clearly labelled AI-derived analysis. Raw evidence and analysis
            are never mixed.
          </p>
          <ul className="mt-8 space-y-3 text-sm opacity-90">
            {[
              "Chronological evidence timeline",
              "Entity and keyword correlation",
              "Analysis flags with source attribution",
            ].map((f) => (
              <li key={f} className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 shrink-0" aria-hidden />
                {f}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs opacity-70">Authorised examiner access only · Activity is logged.</p>
      </section>

      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-3 lg:hidden">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-deep shadow-red">
              <Fingerprint className="h-6 w-6 text-primary-foreground" aria-hidden />
            </span>
            <span>
              <span className="block text-base font-bold tracking-tight text-foreground">
                Evidence Examiner Desk
              </span>
              <span className="label-caps block text-muted-foreground">
                Digital Forensics Platform
              </span>
            </span>
          </div>

          <h1 className="mt-8 text-2xl font-bold tracking-tight text-foreground lg:mt-0">
            Examiner sign in
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your credentials to open the case workspace.
          </p>

          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
            {errors.form && (
              <p
                role="alert"
                className="flex items-start gap-2 rounded-lg border-2 border-ai-border bg-ai px-3 py-2.5 text-sm text-brand-dark"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                {errors.form}
              </p>
            )}

            <div>
              <label htmlFor="email" className="label-caps text-muted-foreground">
                Email or username
              </label>
              <div className="relative mt-1.5">
                <Mail
                  className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground"
                  aria-hidden
                />
                <input
                  id="email"
                  type="text"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="examiner@agency.gov"
                  aria-invalid={Boolean(errors.email)}
                  className={fieldClass(errors.email)}
                />
              </div>
              {errors.email && <p className="mt-1.5 text-xs text-brand-accent">{errors.email}</p>}
            </div>

            <div>
              <label htmlFor="password" className="label-caps text-muted-foreground">
                Password
              </label>
              <div className="relative mt-1.5">
                <Lock
                  className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground"
                  aria-hidden
                />
                <input
                  id="password"
                  type={show ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  aria-invalid={Boolean(errors.password)}
                  className={fieldClass(errors.password)}
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  aria-label={show ? "Hide password" : "Show password"}
                  className="focus-ring absolute right-2 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  {show ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-brand-accent">{errors.password}</p>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 accent-[var(--brand-deep)]"
                />
                Remember me
              </label>
              <button
                type="button"
                onClick={() =>
                  setErrors({
                    form: "Password resets are handled by your case administrator.",
                  })
                }
                className="focus-ring rounded text-sm font-semibold text-brand-deep hover:text-brand-dark"
              >
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              disabled={pending}
              className="focus-ring inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-brand-deep text-sm font-semibold text-primary-foreground transition-colors hover:bg-brand-dark disabled:opacity-60"
            >
              {pending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {pending ? "Verifying…" : "Sign in"}
            </button>

            <p className="text-center text-xs text-muted-foreground">
              Demo access: any email with a password of at least 6 characters.
            </p>
          </form>
        </div>
      </section>
    </div>
  );
}
