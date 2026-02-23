import React from "react";
import {
  CheckCircle2,
  CircleHelp,
  AlertTriangle,
  Folder,
} from "lucide-react";
import type { Service } from "../../schemas/health";
import { getUptime, formatTime } from "../../lib/utils";
import { useState, useEffect } from "react";

// Package info for each service
const PACKAGE_INFO: Record<string, {
  path: string;
  devUrl: string;
  quickActions: { label: string; url: string; external?: boolean }[];
  commands: { label: string; cmd: string }[];
  gettingStarted: string[];
}> = {
  UI: {
    path: "packages/ui/",
    devUrl: "http://localhost:3000",
    quickActions: [
      { label: "Storybook", url: "http://localhost:6006", external: true },
    ],
    commands: [
      { label: "Dev", cmd: "pnpm dev" },
      { label: "Build", cmd: "pnpm build" },
      { label: "Test", cmd: "pnpm test" },
      { label: "Lint", cmd: "pnpm lint" },
      { label: "Format", cmd: "pnpm format" },
      { label: "Type Check", cmd: "pnpm type-check" },
    ],
    gettingStarted: [
      "Create route in `src/routes/`",
      "Add components in `src/components/`",
      "Add API calls in `src/services/`",
      "Create hooks in `src/hooks/` to use services",
    ],
  },
  API: {
    path: "packages/api/",
    devUrl: "http://localhost:8000",
    quickActions: [
      { label: "API Docs", url: "http://localhost:8000/docs", external: true },
      { label: "DB Admin", url: "http://localhost:8000/admin", external: true },
    ],
    commands: [
      { label: "Dev", cmd: "pnpm dev" },
      { label: "Start", cmd: "pnpm start" },
      { label: "Test", cmd: "pnpm test" },
      { label: "Lint", cmd: "pnpm lint" },
      { label: "Format", cmd: "pnpm format" },
      { label: "Type Check", cmd: "pnpm type-check" },
    ],
    gettingStarted: [
      "Create schema in `src/schemas/`",
      "Add route in `src/routes/`",
      "Register router in `main.py`",
    ],
  },
  Database: {
    path: "packages/db/",
    devUrl: "postgresql://localhost:5432",
    quickActions: [],
    commands: [
      { label: "Start DB", cmd: "pnpm db:start" },
      { label: "Stop DB", cmd: "pnpm db:stop" },
      { label: "Logs", cmd: "pnpm db:logs" },
      { label: "Migrate", cmd: "pnpm migrate" },
      { label: "New Migration", cmd: "pnpm migrate:new" },
      { label: "History", cmd: "pnpm migrate:history" },
    ],
    gettingStarted: [
      "See example model in `src/db/models.py`",
      "Add/modify models, then run `pnpm migrate:new`",
      "Apply migration with `pnpm migrate`",
    ],
  },
};

// Parse backtick-wrapped text into styled code segments
function formatWithCode(text: string) {
  const parts = text.split(/(`[^`]+`)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={idx} className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

function DevInfo({ serviceName }: { serviceName: string }) {
  const info = PACKAGE_INFO[serviceName];
  const [showSteps, setShowSteps] = useState(false);

  if (!info) return null;

  return (
    <div className="mt-3 space-y-3">
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        {info.quickActions.map((action, idx) => (
          <a
            key={idx}
            href={action.url}
            target={action.external ? "_blank" : undefined}
            rel={action.external ? "noopener noreferrer" : undefined}
            className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
          >
            {action.label}
            {action.external && <span className="text-[10px]">↗</span>}
          </a>
        ))}
      </div>

      {/* Commands */}
      <div className="flex flex-wrap gap-1.5">
        {info.commands.map((cmd, idx) => (
          <div
            key={idx}
            className="inline-flex items-center gap-1.5 rounded bg-muted px-2 py-1 font-mono text-[11px]"
          >
            <span className="text-muted-foreground">{cmd.label}:</span>
            <code className="text-foreground">{cmd.cmd}</code>
          </div>
        ))}
      </div>

      {/* Getting Started */}
      <div>
        <button
          onClick={() => setShowSteps(!showSteps)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <span>{showSteps ? "▼" : "▶"}</span>
          <span>Getting Started</span>
        </button>
        {showSteps && (
          <ol className="mt-2 ml-4 space-y-1 text-xs text-muted-foreground list-decimal list-outside">
            {info.gettingStarted.map((step, idx) => (
              <li key={idx} className="pl-1">{formatWithCode(step)}</li>
            ))}
          </ol>
        )}
      </div>

      {/* Package Path & Dev URL */}
      <div className="flex flex-col gap-1 text-[11px] font-mono pt-2 border-t border-border">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Folder className="h-3 w-3 text-amber-500" />
          <span>{info.path}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground">Dev:</span>
          {info.devUrl.startsWith("http") ? (
            <a
              href={info.devUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sky-500 hover:underline"
            >
              {info.devUrl}
            </a>
          ) : (
            <span className="text-foreground">{info.devUrl}</span>
          )}
        </div>
      </div>
    </div>
  );
}

const STATUS_META: Record<
  Service["status"],
  { label: string; color: string; dot: string; icon: React.ReactNode }
> = {
  healthy: {
    label: "Healthy",
    color:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    dot: "bg-emerald-500",
    icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
  },
  degraded: {
    label: "Degraded",
    color:
      "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    dot: "bg-amber-500",
    icon: <AlertTriangle className="h-4 w-4 text-amber-500" />,
  },
  down: {
    label: "Down",
    color:
      "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300",
    dot: "bg-rose-500",
    icon: <AlertTriangle className="h-4 w-4 text-rose-500" />,
  },
  unknown: {
    label: "Unknown",
    color:
      "bg-slate-100 text-slate-700 dark:bg-slate-900/60 dark:text-slate-300",
    dot: "bg-slate-400",
    icon: <CircleHelp className="h-4 w-4 text-slate-400" />,
  },
};

export function ServiceCard({ 
  service, 
  isLoading, 
  error 
}: { 
  service: Service; 
  isLoading: boolean;
  error?: Error | null;
}) {
  const meta = STATUS_META[service.status];
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setUptime(getUptime(new Date(service.start_time)));
    }, 1000);
    return () => clearInterval(interval);
  }, [service.start_time]);

  const uptimeString = formatTime(uptime);

  return (
    <div className="group relative overflow-hidden rounded-xl border bg-card p-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-sky-500/0 via-sky-500/60 to-fuchsia-500/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-muted ring-1 ring-border">
            {isLoading ? (
              <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
            ) : (
              STATUS_META[service.status].icon
            )}
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {service.name}
              </span>
              {isLoading ? (
                <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium bg-muted text-muted-foreground">
                  <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-pulse"></div>
                  Checking...
                </span>
              ) : (
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${meta.color}`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${meta.dot}`}
                  ></span>
                  {meta.label}
                </span>
              )}
            </div>
            <span className="text-xs text-muted-foreground">
              {service.message}
            </span>
            {error && !isLoading && (
              <span className="text-xs text-destructive mt-1">
                {error.message}
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              {uptimeString}
            </span>
          </div>
        </div>
      </div>
      <DevInfo serviceName={service.name} />
    </div>
  );
}