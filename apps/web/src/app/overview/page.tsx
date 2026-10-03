"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Shell, Card, Kpi } from "@/components/shell";
import { apiGet, apiPost } from "@/lib/api";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const IndiaMap = dynamic(() => import("@/components/india-map").then((m) => m.IndiaMap), { ssr: false });

type Overview = {
  kpis: {
    active_models: number;
    blended_locations: number;
    highest_risk_event: { type: string; location: string; probability: number } | null;
    forecast_reliability: number;
    model_disagreement: number;
    latest_update: string;
    models_degraded: number;
    observations_processed: number;
  };
  contribution: { nwp: number; ai: number; ens: number };
  banner: string;
};

type ForecastList = {
  items: Array<{
    location_id: string;
    name: string;
    lat: number;
    lon: number;
    value: number;
    dominant_model: string;
    frs: number;
    disagreement: number;
    failure_risk: string;
    weights: Record<string, number>;
  }>;
};

type WeightHistory = {
  series: Array<Record<string, number | string>>;
};

const MODEL_COLORS: Record<string, string> = {
  nwp: "#22d3ee",
  ai: "#34d399",
  ens: "#a78bfa",
};

const RISK_COLOR: Record<string, string> = {
  HIGH: "#f87171",
  MODERATE: "#fbbf24",
  LOW: "#34d399",
};

export default function OverviewPage() {
  const q = useQuery({
    queryKey: ["overview"],
    queryFn: () => apiGet<Overview>("/api/v1/overview"),
    refetchInterval: 30000,
  });
  const fc = useQuery({
    queryKey: ["fc-rain-48"],
    queryFn: () => apiGet<ForecastList>("/api/v1/forecast?variable=RAINFALL&lead_time_hours=48"),
  });
  const ev = useQuery({
    queryKey: ["events"],
    queryFn: () =>
      apiGet<{
        items: Array<{
          event_id: string;
          event_type: string;
          location_name: string;
          probability: number;
          confidence: string;
          forecast_failure_risk: string;
        }>;
      }>("/api/v1/extremes"),
  });
  const wh = useQuery({
    queryKey: ["wh-del"],
    queryFn: () => apiGet<WeightHistory>("/api/v1/weights/history?location_id=IN-DL-DEL&variable=RAINFALL"),
  });
  const seed = useMutation({ mutationFn: () => apiPost("/api/v1/admin/seed") });

  const k = q.data?.kpis;

  const mapPoints =
    fc.data?.items?.slice(0, 120).map((p) => ({
      id: p.location_id,
      lat: p.lat,
      lon: p.lon,
      value: p.value,
      label: p.name,
      extra: `${p.value?.toFixed?.(1)} mm · FRS ${p.frs ?? "—"} · ${p.dominant_model?.split("-")[0]}`,
      color:
        p.failure_risk === "HIGH"
          ? "#f87171"
          : p.dominant_model?.startsWith("ai")
            ? "#34d399"
            : p.dominant_model?.startsWith("nwp")
              ? "#22d3ee"
              : "#a78bfa",
    })) ?? [];

  // Contribution pie
  const contrib = q.data?.contribution;
  const pieData = contrib
    ? [
        { name: "NWP", value: Math.round((contrib.nwp || 0) * 100), color: "#22d3ee" },
        { name: "AI", value: Math.round((contrib.ai || 0) * 100), color: "#34d399" },
        { name: "Ensemble", value: Math.round((contrib.ens || 0) * 100), color: "#a78bfa" },
      ]
    : [];

  // Weight evolution data
  const wSeries = wh.data?.series ?? [];

  return (
    <Shell>
      {/* Header */}
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Adaptive Forecast Intelligence</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            One forecast is not always enough. The best model changes with context.
          </p>
        </div>
        <button
          onClick={() => seed.mutate()}
          disabled={seed.isPending}
          className="rounded border border-cyan-500/40 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200 hover:bg-cyan-500/20 transition-colors disabled:opacity-60"
        >
          {seed.isPending ? "Seeding benchmark…" : "Load / refresh demo data"}
        </button>
      </div>

      {seed.isError && (
        <div className="mb-4 rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          Seed failed — ensure the API is running (see README / Docker Compose).
        </div>
      )}
      {seed.isSuccess && (
        <div className="mb-4 rounded border border-green-500/40 bg-green-500/10 px-3 py-2 text-sm text-green-300">
          Demo benchmark loaded successfully. All pages are now populated.
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-5">
        <Kpi label="Active models" value={k?.active_models ?? "—"} />
        <Kpi label="Blended locations" value={k?.blended_locations ?? "—"} />
        <Kpi
          label="Forecast reliability"
          value={k ? `${k.forecast_reliability}` : "—"}
          hint="FRS — decision-support summary 0–100"
        />
        <Kpi
          label="Model disagreement"
          value={k ? k.model_disagreement.toFixed(3) : "—"}
          hint="0 = full agreement · 1 = maximum spread"
        />
        <Kpi
          label="Models degraded"
          value={k?.models_degraded ?? "—"}
          hint="Health monitor; affects weights"
        />
        <Kpi label="Observations processed" value={k?.observations_processed ?? "—"} />
        <Kpi
          label="Latest pipeline run"
          value={k?.latest_update ? k.latest_update.slice(0, 16) + "Z" : "—"}
        />
        <Kpi
          label="Highest-risk event"
          value={k?.highest_risk_event ? k.highest_risk_event.type.replace("_", " ") : "—"}
          hint={
            k?.highest_risk_event
              ? `${k.highest_risk_event.location} · p=${(k.highest_risk_event.probability * 100).toFixed(0)}%`
              : undefined
          }
        />
      </div>

      {/* Main content grid */}
      <div className="grid gap-4 lg:grid-cols-3 mb-4">
        {/* India Map */}
        <Card title="India rainfall 48h — AERIS blend" className="lg:col-span-2">
          <p className="mb-2 text-[11px] text-slate-500">
            Color: green=AI dominant · cyan=NWP dominant · violet=ensemble dominant · red=high failure risk
          </p>
          <IndiaMap points={mapPoints} />
        </Card>

        {/* Model contribution pie */}
        <Card title="Mean model contribution (48h rainfall)">
          {pieData.length > 0 ? (
            <>
              <div className="h-40">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} label={({ name, value }) => `${name} ${value}%`} labelLine={false} fontSize={11}>
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => `${v}%`} contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 space-y-2">
                {pieData.map((d) => (
                  <div key={d.name}>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-400">{d.name}</span>
                      <span style={{ color: d.color }}>{d.value}%</span>
                    </div>
                    <div className="mt-0.5 h-1.5 rounded bg-navy-700">
                      <div className="h-1.5 rounded" style={{ width: `${d.value}%`, background: d.color }} />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[11px] text-slate-500">
                Weights are always ≥ 0 and sum to 1. Context-aware dynamic weighting.
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-500">Seed demo data to populate.</p>
          )}
        </Card>
      </div>

      {/* Weight evolution + events */}
      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        {/* Dynamic weight evolution across lead times */}
        <Card title="Weight evolution across lead times — New Delhi, rainfall">
          {wSeries.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <AreaChart data={wSeries} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="lead" stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `${v}h`} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} unit="%" />
                  <Tooltip
                    formatter={(v: number) => `${v?.toFixed?.(1)}%`}
                    contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {["nwp", "ai", "ens"].map((m) => (
                    <Area
                      key={m}
                      type="monotone"
                      dataKey={m}
                      stackId="1"
                      stroke={MODEL_COLORS[m]}
                      fill={MODEL_COLORS[m]}
                      fillOpacity={0.5}
                      name={m.toUpperCase()}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">
              Seed demo data to see weight evolution.
            </div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            Dynamic trust engine redistributes weights across lead times based on regime, health and skill.
          </p>
        </Card>

        {/* Extreme events */}
        <Card title="Current major extreme events">
          {(ev.data?.items ?? []).length > 0 ? (
            <div className="space-y-2">
              {(ev.data?.items ?? []).slice(0, 6).map((e) => (
                <div
                  key={e.event_id}
                  className="flex items-center justify-between rounded border border-white/5 bg-navy-900/60 px-3 py-2"
                >
                  <div>
                    <div className="text-sm font-medium text-white capitalize">
                      {e.event_type.replace("_", " ")}
                    </div>
                    <div className="text-xs text-slate-400">{e.location_name}</div>
                    <div className="text-[11px] text-slate-500">{e.confidence} confidence</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-semibold" style={{ color: RISK_COLOR[e.forecast_failure_risk] ?? "#22d3ee" }}>
                      {(e.probability * 100).toFixed(0)}%
                    </div>
                    <div className="text-[11px]" style={{ color: RISK_COLOR[e.forecast_failure_risk] ?? "#94a3b8" }}>
                      {e.forecast_failure_risk} risk
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Seed demo data to populate events.</p>
          )}
          <Link className="mt-3 inline-block text-xs text-cyan-400 hover:text-cyan-300" href="/events">
            Open event intelligence →
          </Link>
        </Card>
      </div>

      {/* Demo flow guide */}
      <Card title="5-minute demonstration path">
        <ol className="grid gap-1.5 text-sm text-slate-300 md:grid-cols-2 list-decimal pl-5">
          {[
            ["Overview (this page)", "/overview", "India rainfall 48h · model contribution"],
            ["Forecast Explorer", "/forecast", "Compare NWP / AI / ensemble / AERIS"],
            ["India GIS", "/gis", "Layers: forecast · FRS · disagreement · risk"],
            ["Weather Regimes", "/regimes", "Operational regime classes + transition"],
            ["Model Health", "/model-health", "Health scores driving trust adjustment"],
            ["Dynamic Weight Maps", "/weights", "Spatially smoothed model trust fields"],
            ["Extreme Events", "/events", "Heavy rain · heatwave · high wind cards"],
            ["Uncertainty & FRS", "/uncertainty", "Forecast value ≠ confidence ≠ uncertainty"],
            ["Counterfactual Lab", "/lab", "SIMULATION — remove model, change weights"],
            ["Verification", "/verification", "AERIS vs individual — DEMONSTRATION BENCHMARK"],
            ["Model Registry", "/registry", "MLflow artifacts · trust meta-model"],
            ["System Health", "/system", "API · DB · Redis · pipeline jobs"],
          ].map(([label, href, hint]) => (
            <li key={href as string}>
              <Link className="text-cyan-400 hover:text-cyan-300" href={href as string}>
                {label as string}
              </Link>
              <span className="ml-1 text-slate-500 text-xs">— {hint as string}</span>
            </li>
          ))}
        </ol>
      </Card>
    </Shell>
  );
}
