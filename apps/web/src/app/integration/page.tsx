"use client";

import { useState } from "react";
import { Shell, Card } from "@/components/shell";
import { API_BASE } from "@/lib/api";

const ENDPOINTS = [
  {
    method: "GET",
    path: "/api/v1/health",
    desc: "API + DB + Redis health check with latency",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/meta",
    desc: "Product metadata: name, PS number, core messages",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/models",
    desc: "List all registered forecast sources",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/models/{id}",
    desc: "Single model: health, skill, metadata",
    params: ["id"],
  },
  {
    method: "GET",
    path: "/api/v1/forecast",
    desc: "Blended forecast for location + variable + lead",
    params: ["location_id", "variable", "lead_time_hours", "model"],
  },
  {
    method: "POST",
    path: "/api/v1/forecast/blend",
    desc: "Trigger blend for a specific request body",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/forecast/skill-lead",
    desc: "MAE vs lead time per model for line chart",
    params: ["variable", "region"],
  },
  {
    method: "GET",
    path: "/api/v1/forecast/uncertainty-series",
    desc: "Uncertainty interval across lead times",
    params: ["location_id", "variable"],
  },
  {
    method: "GET",
    path: "/api/v1/weights",
    desc: "Dynamic trust weights for all locations",
    params: ["variable", "lead_time_hours"],
  },
  {
    method: "GET",
    path: "/api/v1/weights/history",
    desc: "Weight evolution across lead times (chart data)",
    params: ["location_id", "variable"],
  },
  {
    method: "GET",
    path: "/api/v1/reliability",
    desc: "FRS for all locations",
    params: ["location_id", "variable", "lead_time_hours"],
  },
  {
    method: "GET",
    path: "/api/v1/disagreement",
    desc: "Inter-model disagreement scores",
    params: ["variable", "lead_time_hours"],
  },
  {
    method: "GET",
    path: "/api/v1/extremes",
    desc: "Extreme weather events (heavy rain/heat/wind)",
    params: ["event_type"],
  },
  {
    method: "GET",
    path: "/api/v1/regimes",
    desc: "Weather regime per location + transition probability",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/verification",
    desc: "Overall verification metrics per model",
    params: ["variable", "region"],
  },
  {
    method: "GET",
    path: "/api/v1/verification/by-lead",
    desc: "MAE by lead time per model (chart data)",
    params: ["variable"],
  },
  {
    method: "GET",
    path: "/api/v1/skill",
    desc: "Rolling skill memory — full table",
    params: ["model_id"],
  },
  {
    method: "GET",
    path: "/api/v1/skill/heatmap",
    desc: "MAE grid: model × lead time",
    params: ["variable"],
  },
  {
    method: "GET",
    path: "/api/v1/model-health",
    desc: "Health score + status + reasons per model",
    params: [],
  },
  {
    method: "POST",
    path: "/api/v1/simulations/counterfactual",
    desc: "Counterfactual: remove models, adjust weights, compare strategies",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/provenance/{forecast_id}",
    desc: "Full data lineage for a blended forecast",
    params: ["forecast_id"],
  },
  {
    method: "GET",
    path: "/api/v1/overview",
    desc: "KPIs, contribution summary, highest-risk event",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/timeseries",
    desc: "Multi-model time series at a location",
    params: ["location_id", "variable"],
  },
  {
    method: "GET",
    path: "/api/v1/ml/registry",
    desc: "Trust meta-model registry (MLflow integration)",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/system",
    desc: "Infrastructure health, pipeline jobs, alerts",
    params: [],
  },
  {
    method: "GET",
    path: "/api/v1/data-hub",
    desc: "Forecast source status, variables, quality",
    params: [],
  },
  {
    method: "WS",
    path: "/api/v1/ws",
    desc: "WebSocket: live forecast/health/event/pipeline updates",
    params: [],
  },
];

const METHOD_COLORS: Record<string, string> = {
  GET: "#34d399",
  POST: "#fbbf24",
  WS: "#a78bfa",
};

export default function IntegrationPage() {
  const [filter, setFilter] = useState("");

  const filtered = ENDPOINTS.filter(
    (e) =>
      !filter ||
      e.path.toLowerCase().includes(filter.toLowerCase()) ||
      e.desc.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <Shell>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-white">API / Integration</h1>
        <p className="mt-0.5 text-sm text-slate-400">
          Full REST API surface with OpenAPI documentation. Validated with Pydantic v2.
          All responses include{" "}
          <code className="text-xs bg-navy-700 px-1 py-0.5 rounded">data_mode</code> and{" "}
          <code className="text-xs bg-navy-700 px-1 py-0.5 rounded">banner</code> fields.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3 mb-5">
        <Card>
          <div className="text-[11px] uppercase tracking-wider text-slate-500">OpenAPI docs</div>
          <div className="mt-2">
            <a
              className="text-cyan-400 hover:text-cyan-300 text-sm font-medium transition-colors"
              href={`${API_BASE}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              {API_BASE}/docs ↗
            </a>
          </div>
          <div className="mt-1 text-xs text-slate-500">Swagger UI — interactive endpoint tester</div>
        </Card>
        <Card>
          <div className="text-[11px] uppercase tracking-wider text-slate-500">ReDoc</div>
          <div className="mt-2">
            <a
              className="text-cyan-400 hover:text-cyan-300 text-sm font-medium transition-colors"
              href={`${API_BASE}/redoc`}
              target="_blank"
              rel="noreferrer"
            >
              {API_BASE}/redoc ↗
            </a>
          </div>
          <div className="mt-1 text-xs text-slate-500">Clean API reference documentation</div>
        </Card>
        <Card>
          <div className="text-[11px] uppercase tracking-wider text-slate-500">WebSocket</div>
          <div className="mt-2 font-mono text-xs text-slate-300 break-all">
            {typeof window !== "undefined"
              ? API_BASE.replace("http", "ws")
              : "ws://localhost:8000"}
            /api/v1/ws
          </div>
          <div className="mt-1 text-xs text-slate-500">Live forecast / health / event pings</div>
        </Card>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search endpoints…"
          className="w-full rounded border border-cyan-900/40 bg-navy-800 px-4 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/60"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {/* Endpoint table */}
      <Card title={`API surface — ${filtered.length} endpoints`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-white/10">
                <th className="pb-2 pr-3 w-12">Method</th>
                <th className="pb-2 pr-3">Path</th>
                <th className="pb-2 pr-3">Description</th>
                <th className="pb-2">Params</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr key={e.path} className="border-t border-white/5 hover:bg-white/2">
                  <td className="py-2 pr-3">
                    <span
                      className="rounded px-1.5 py-0.5 text-[10px] font-bold font-mono"
                      style={{
                        color: METHOD_COLORS[e.method] ?? "#94a3b8",
                        background: (METHOD_COLORS[e.method] ?? "#94a3b8") + "22",
                      }}
                    >
                      {e.method}
                    </span>
                  </td>
                  <td className="py-2 pr-3 font-mono text-cyan-300">{e.path}</td>
                  <td className="py-2 pr-3 text-slate-300">{e.desc}</td>
                  <td className="py-2 text-slate-500">{e.params.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Integration architecture */}
      <Card title="Integration architecture" className="mt-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="space-y-3">
            <div>
              <div className="font-medium text-cyan-300 mb-1">Authentication</div>
              <div className="text-xs text-slate-400">
                Basic auth placeholder in config. RBAC-ready architecture: ADMIN · ANALYST · RESEARCHER · VIEWER.
                Set <code className="bg-navy-700 px-1 rounded">AUTH_DISABLED=false</code> and configure roles for production.
              </div>
            </div>
            <div>
              <div className="font-medium text-cyan-300 mb-1">CORS</div>
              <div className="text-xs text-slate-400">
                Configurable via <code className="bg-navy-700 px-1 rounded">CORS_ORIGINS</code> env variable.
                Default: <code className="bg-navy-700 px-1 rounded">http://localhost:3000</code>.
              </div>
            </div>
            <div>
              <div className="font-medium text-cyan-300 mb-1">Rate limiting</div>
              <div className="text-xs text-slate-400">
                Hook point implemented. Wire to Redis-backed slowapi or similar for production.
              </div>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <div className="font-medium text-cyan-300 mb-1">Request tracing</div>
              <div className="text-xs text-slate-400">
                Every request gets a <code className="bg-navy-700 px-1 rounded">x-request-id</code> header.
                Response includes <code className="bg-navy-700 px-1 rounded">x-aeris-data-mode</code>.
                Structured JSON logging to stdout.
              </div>
            </div>
            <div>
              <div className="font-medium text-cyan-300 mb-1">Error format</div>
              <div className="text-xs text-slate-400">
                <code className="bg-navy-700 px-1 rounded">{"{ error, request_id, detail }"}</code> — no stack traces in responses.
              </div>
            </div>
            <div>
              <div className="font-medium text-cyan-300 mb-1">Data mode header</div>
              <div className="text-xs text-slate-400">
                Every response body includes <code className="bg-navy-700 px-1 rounded">data_mode</code> and <code className="bg-navy-700 px-1 rounded">banner</code>.
                Consumers can always detect demonstration vs operational context.
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Future integrations */}
      <Card title="Future operational integration points" className="mt-4">
        <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["NCMRWF NWP", "Configure RealNWPAdapter with NWP_BASE_URL + NWP_API_KEY. No engine change."],
            ["ECMWF / GFS", "Add new adapter implementing BaseForecastAdapter. Auto-registered."],
            ["Satellite / Radar", "SatelliteAdapter + RadarAdapter stubs ready. Wire ingest pipeline."],
            ["Station observations", "ObservationAdapter stub ready. Replace MockObservationAdapter."],
            ["Kafka / NATS streaming", "Replace Celery ingestion tasks with streaming consumer."],
            ["Kubernetes / HPC", "Docker Compose → Helm chart. Services are stateless and horizontally scalable."],
          ].map(([title, desc]) => (
            <div key={title as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium text-cyan-300 mb-1">{title as string}</div>
              <div className="text-slate-400">{desc as string}</div>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
