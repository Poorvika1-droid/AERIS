"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Shell, Card, Kpi } from "@/components/shell";
import { apiGet, apiPost } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  ok: "#34d399",
  error: "#f87171",
  unavailable: "#fbbf24",
  degraded: "#fbbf24",
  SUCCESS: "#34d399",
  FAILURE: "#f87171",
  RUNNING: "#22d3ee",
};

type SysData = {
  health: {
    status: string;
    api: string;
    database: string;
    redis: string;
    mlflow: string;
    data_mode: string;
    latency_ms: number;
    banner: string;
  };
  jobs: Array<{
    id: string;
    name: string;
    status: string;
    detail: string;
    started: string;
  }>;
  metrics: Array<{ name: string; value: number }>;
  alerts: Array<{ level: string; message: string; at: string }>;
  queue: { broker: string; note: string };
};

export default function SystemPage() {
  const q = useQuery({
    queryKey: ["sys"],
    queryFn: () => apiGet<SysData>("/api/v1/system"),
    refetchInterval: 10000,
  });

  const learn = useMutation({ mutationFn: () => apiPost("/api/v1/admin/learn") });
  const seed = useMutation({ mutationFn: () => apiPost("/api/v1/admin/seed") });

  const h = q.data?.health;
  const jobs = q.data?.jobs ?? [];
  const alerts = q.data?.alerts ?? [];

  const services = h
    ? [
        { name: "API", status: h.api, hint: `Latency ${h.latency_ms} ms` },
        { name: "Database", status: h.database, hint: "PostgreSQL / SQLite demo" },
        { name: "Redis", status: h.redis, hint: "Cache + message broker" },
        { name: "MLflow", status: h.mlflow ? "configured" : "unavailable", hint: h.mlflow },
        { name: "Data mode", status: h.data_mode, hint: h.banner },
        { name: "Overall", status: h.status, hint: "" },
      ]
    : [];

  const ALERT_COLORS: Record<string, string> = {
    INFO: "#22d3ee",
    WARNING: "#fbbf24",
    ERROR: "#f87171",
    CRITICAL: "#dc2626",
  };

  return (
    <Shell>
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">System health</h1>
          <p className="mt-0.5 text-sm text-slate-400">
            Infrastructure status, pipeline jobs, continuous learning trigger.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => learn.mutate()}
            disabled={learn.isPending}
            className="rounded border border-cyan-500/40 px-3 py-1.5 text-sm text-cyan-200 hover:bg-cyan-500/10 transition-colors disabled:opacity-50"
          >
            {learn.isPending ? "Recalibrating…" : "▶ Run learning step"}
          </button>
          <button
            onClick={() => seed.mutate()}
            disabled={seed.isPending}
            className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            {seed.isPending ? "Seeding…" : "↺ Re-seed demo data"}
          </button>
        </div>
      </div>

      {/* Service status */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 mb-5">
        {services.map((s) => (
          <div key={s.name} className="rounded-lg border border-cyan-900/25 bg-navy-800 px-4 py-3">
            <div className="text-[11px] uppercase tracking-wider text-slate-500">{s.name}</div>
            <div
              className="mt-1 text-lg font-semibold"
              style={{ color: STATUS_COLORS[s.status] ?? "#94a3b8" }}
            >
              {s.status}
            </div>
            <div className="mt-0.5 text-[11px] text-slate-500 truncate">{s.hint}</div>
          </div>
        ))}
      </div>

      {learn.isSuccess && (
        <div className="mb-4 rounded border border-green-500/40 bg-green-500/10 px-3 py-2 text-sm text-green-300">
          Learning step complete — skill memory, health, blend, and verification updated.
          Elapsed: {(learn.data as { elapsed_s?: number })?.elapsed_s ?? "—"}s
        </div>
      )}

      {/* Queue info */}
      <Card title="Message queue & worker" className="mb-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Broker</div>
            <div className="font-mono text-xs text-slate-300">{q.data?.queue?.broker ?? "—"}</div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Note</div>
            <div className="text-xs text-slate-400">{q.data?.queue?.note}</div>
          </div>
        </div>
        <div className="mt-3 text-[11px] text-slate-500">
          Celery worker optional in demo mode. POST /api/v1/admin/learn triggers a synchronous learning step.
          In production: schedule via Celery beat or Airflow DAG.
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        {/* Pipeline jobs */}
        <Card title="Recent pipeline jobs">
          {jobs.length > 0 ? (
            <div className="space-y-2">
              {jobs.slice(0, 10).map((j) => (
                <div key={j.id} className="flex items-start justify-between rounded border border-white/5 bg-navy-900/60 px-3 py-2 text-xs">
                  <div>
                    <div className="font-medium text-slate-200">{j.name}</div>
                    <div className="text-slate-500 mt-0.5">{j.detail}</div>
                    <div className="text-slate-600 mt-0.5 font-mono">{j.started?.slice(0, 16)}Z</div>
                  </div>
                  <div
                    className="rounded px-2 py-0.5 text-[10px] font-semibold ml-2 shrink-0"
                    style={{
                      color: STATUS_COLORS[j.status] ?? "#94a3b8",
                      background: (STATUS_COLORS[j.status] ?? "#94a3b8") + "22",
                    }}
                  >
                    {j.status}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No jobs recorded yet.</p>
          )}
        </Card>

        {/* Alerts */}
        <Card title="System alerts">
          {alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.slice(0, 10).map((a, i) => (
                <div key={i} className="flex items-start gap-2 rounded border border-white/5 bg-navy-900/60 px-3 py-2 text-xs">
                  <div
                    className="rounded px-1.5 py-0.5 text-[10px] font-semibold shrink-0"
                    style={{
                      color: ALERT_COLORS[a.level] ?? "#94a3b8",
                      background: (ALERT_COLORS[a.level] ?? "#94a3b8") + "22",
                    }}
                  >
                    {a.level}
                  </div>
                  <div>
                    <div className="text-slate-300">{a.message}</div>
                    <div className="text-slate-500 mt-0.5">{a.at?.slice(0, 16)}Z</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No alerts.</p>
          )}
        </Card>
      </div>

      {/* Continuous learning explanation */}
      <Card title="Continuous learning cycle">
        <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["1. FORECAST", "AERIS blend produced from dynamic trust weights", "#22d3ee"],
            ["2. OBSERVATION", "Station/grid observations arrive (real or demo)", "#34d399"],
            ["3. ERROR ANALYSIS", "Forecast vs observation → MAE, RMSE, bias, CSI per model×region×lead×regime", "#a78bfa"],
            ["4. SKILL UPDATE + RECALIBRATE", "Rolling skill memory updated → weights recalibrated → next forecast", "#fbbf24"],
          ].map(([step, desc, color]) => (
            <div key={step as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-semibold mb-1" style={{ color: color as string }}>{step as string}</div>
              <div className="text-xs text-slate-400 leading-relaxed">{desc as string}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          Prototype: rolling skill + health + blend update on each trigger. 
          No huge model retraining on every observation — meta-model retrained on schedule when sufficient labeled data exists.
        </p>
      </Card>
    </Shell>
  );
}
