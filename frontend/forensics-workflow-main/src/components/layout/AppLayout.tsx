import { useState } from "react";
import type { ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import { Fingerprint, HardDrive, LogOut, Menu, X, UserRound } from "lucide-react";
import { NAV_ITEMS } from "./nav-items";
import { useAuth } from "@/lib/auth";
import { useReport } from "@/lib/use-report";
import { cn } from "@/lib/utils";

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <nav className="flex-1 space-y-1 p-3" aria-label="Main navigation">
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.to;
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            title={item.description}
            aria-current={active ? "page" : undefined}
            className={cn(
              "focus-ring flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors",
              active
                ? "bg-brand-deep text-primary-foreground shadow-red"
                : "text-muted-foreground hover:bg-ai hover:text-brand-dark",
            )}
          >
            <item.icon className="h-4 w-4 shrink-0" aria-hidden />
            <span className="truncate">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarFooter() {
  const { user, logout } = useAuth();

  return (
    <div className="border-t border-border p-3">
      <div className="flex min-w-0 items-center gap-3 rounded-lg bg-muted px-3 py-2.5">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-deep text-primary-foreground">
          <UserRound className="h-4 w-4" aria-hidden />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold text-foreground">
            {user?.name ?? "Investigator"}
          </span>
          <span className="block truncate text-xs text-muted-foreground">{user?.email}</span>
        </span>
      </div>
      <button
        type="button"
        onClick={logout}
        className="focus-ring mt-2 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-muted-foreground transition-colors hover:bg-ai hover:text-brand-dark"
      >
        <LogOut className="h-4 w-4" aria-hidden />
        Logout
      </button>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex min-w-0 items-center gap-3 border-b border-border px-4 py-4">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-deep shadow-red">
        <Fingerprint className="h-5 w-5 text-primary-foreground" aria-hidden />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-bold tracking-tight text-foreground">
          Evidence Examiner Desk
        </span>
        <span className="label-caps block truncate text-muted-foreground">Forensics Platform</span>
      </span>
    </div>
  );
}

export function AppLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const report = useReport();

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-card lg:flex">
        <Brand />
        <NavList />
        <SidebarFooter />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-foreground/40"
          />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-card shadow-raised">
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <Brand />
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close navigation"
                className="focus-ring mr-2 grid h-9 w-9 shrink-0 place-items-center rounded-md text-muted-foreground hover:bg-muted"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>
            <NavList onNavigate={() => setOpen(false)} />
            <SidebarFooter />
          </div>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-border bg-card/95 backdrop-blur">
          <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 sm:px-6">
            <button
              type="button"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
              className="focus-ring grid h-9 w-9 place-items-center rounded-md border border-border text-foreground hover:bg-muted lg:hidden"
            >
              <Menu className="h-5 w-5" aria-hidden />
            </button>
            <span className="min-w-0 truncate text-sm font-bold tracking-tight text-foreground lg:text-base">
              Evidence Examiner Desk
            </span>
            <span className="flex shrink-0 items-center gap-2 rounded-full border border-ai-border bg-ai px-3 py-1.5">
              <HardDrive className="h-4 w-4 text-brand-deep" aria-hidden />
              <span className="label-caps text-brand-dark">Device {report.device_id}</span>
            </span>
          </div>
          <div className="h-0.5 w-full bg-brand-deep" />
        </header>

        <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
