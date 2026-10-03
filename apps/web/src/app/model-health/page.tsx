"use client";

import { useQuery } from "@tanstack/react-query";
import { Shell, Card } from "@/components/shell";
import { apiGet } from "@/lib/api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

const MODEL_COLORS: Record<string, string> = {
  "nwp-mock-gfs-like": "#22d3ee",
  "ai-mock-emulator": "#34d399",
  "ens-mock-mean": "#a78bfa",
};
const MODEL_LABELS: Record<string, string> = {
  "nwp-mock-gfs-like": "NWP",
  "ai-mock-emulator": "AI",
  "ens-mock-mean": "Ensemble",
};

const STATUS_COLORS: Record<string, string> = {
  HEALTHY: "#34d399",
  WARNING: "#fbbf24",
  DEGRADED: "#f87171",
  UNAVAILABLE: "#6b7280",
  ACTIVE: "#34d399",
};

type HealthItem = {
  model_id: string;
  health_score: number;
  health_status: string;
  reasons: string[];
  weight_adjustment: number;
  checked_at: string;
};

type SkillHeatmap = {
  models: string[];
  leads: number[];
  grid: Record<string, Record<number, number>>;
};

export default function ModelHealthPage() {
  const q = useQuery({
    queryKey: ["mh"],
    queryFn: () => apiGet<{ items: HealthItem[] }>("/api/v1/model-health"),
    refetchInterval: 15000,
  });

  const hmap = useQuery({
    queryKey: ["hmap-rain"],
    queryFn: () => apiGet<SkillHeatmap>("/api/v1/skill/heatmap?variable=RAINFALL"),
  });

  const items = q.data?.items ?? [];

  // Gauge data for radial charts
  const gaugeData = items.map((m) => ({
    name: MODEL_LABELS[m.model_id] ?? m.model_id,
    value: m.health_score,
    fill: STATUS_COLORS[m.health_status] ?? "#94a3b8",
  }));

  // Weight adjustment bar chart
  const adjData = items.map((m) => ({
    name: MODEL_LABELS[m.model_id] ?? m.model_id,
    "Weight adjustment": parseFloat((m.weight_adjustment * 100).toFixed(1)),
    color: MODEL_COLORS[m.model_id] ?? "#94a3b8",
  }));

  // Skill heatmap data flattened for bar chart
  const hmapItems = hmap.data;
  const hmapChartData =
    hmapItems
      ? hmapItems.leads.map((l) => {
          const pt: Record<string, string | number> = { lead: `${l}h` };
          hmapItems.models.forEach((m) => {
            const mae = hmapItems.grid[m]?.[l];
            if (mae != null) pt[MODEL_LABELS[m] ?? m] = parseFloat(mae.toFixed(3));
          });
          return pt;
        })
      : [];

  return (
    <Shell>
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Model health monitor</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Health scores directly influence dynamic trust weights. A degraded model gets reduced weight.
          </p>
        </div>
        <div className="text-xs text-slate-500">Auto-refresh every 15 s</div>
      </div>

      {/* Health score gauges */}
      <div className="grid gap-4 md:grid-cols-3 mb-5">
        {items.map((m) => (
          <Card key={m.model_id} className="relative overflow-hidden">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="font-semibold text-white">{MODEL_LABELS[m.model_id] ?? m.model_id}</div>
                <div className="text-xs text-slate-500">{m.model_id}</div>
              </div>
              <div
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  color: STATUS_COLORS[m.health_status] ?? "#94a3b8",
                  background: (STATUS_COLORS[m.health_status] ?? "#94a3b8") + "22",
                }}
              >
                {m.health_status}
              </div>
            </div>

            <div className="h-28">
              <ResponsiveContainer>
                <RadialBarChart
                  cx="50%"
                  cy="100%"
                  innerRadius="60%"
                  outerRadius="100%"
                  startAngle={180}
                  endAngle={0}
                  data={[{ value: m.health_score, fill: STATUS_COLORS[m.health_status] ?? "#94a3b8" }]}
                >
                  <RadialBar dataKey="value" background={{ fill: "#1a2740" }} cornerRadius={4} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>

            <div className="text-center -mt-8 pb-2">
              <div
                className="text-3xl font-semibold"
                style={{ color: STATUS_COLORS[m.health_status] ?? "#94a3b8" }}
              >
                {m.health_score.toFixed(0)}
              </div>
              <div className="text-xs text-slate-500">/ 100</div>
            </div>

            <div className="mt-3 space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Weight adjustment</span>
                <span
                  className="font-mono"
                  style={{ color: m.weight_adjustment < 0.9 ? "#fbbf24" : "#34d399" }}
                >
                  ×{m.weight_adjustment.toFixed(3)}
                </span>
              </div>
              <div className="text-xs text-slate-500">
                Checked: {m.checked_at?.slice(0, 16)}Z
              </div>
            </div>

            <div className="mt-3">
              <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Health reasons</div>
              <ul className="space-y-0.5">
                {m.reasons.map((r, i) => (
                  <li key={i} className="text-xs flex items-start gap-1.5">
                    <span className={m.health_status === "HEALTHY" ? "text-green-400" : "text-amber-400"}>
                      {m.health_status === "HEALTHY" ? "✓" : "⚠"}
                    </span>
                    <span className="text-slate-300">{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        ))}
        {items.length === 0 && (
          <div className="col-span-3 text-center py-12 text-slate-500 text-sm">
            Seed demo data from the Overview page to populate health scores.
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        {/* Weight adjustment comparison */}
        <Card title="Recommended weight adjustment (×1.0 = nominal)">
          {adjData.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <BarChart data={adjData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 120]} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                    formatter={(v: number) => [`${v}%`, "Adj"]}
                  />
                  <Bar dataKey="Weight adjustment" radius={[3, 3, 0, 0]}>
                    {adjData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={entry["Weight adjustment"] < 90 ? "#f87171" : entry["Weight adjustment"] < 100 ? "#fbbf24" : "#34d399"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            &lt; 100% means the trust engine reduces that model's weight. 0 = excluded from blend.
          </p>
        </Card>

        {/* Skill heatmap — MAE grid */}
        <Card title="Skill heatmap — rainfall MAE by lead time">
          {hmapChartData.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <BarChart data={hmapChartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="lead" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="NWP" fill="#22d3ee" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="AI" fill="#34d399" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Ensemble" fill="#a78bfa" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            Lower MAE = better skill. Controls how skill memory contributes to dynamic weights.
          </p>
        </Card>
      </div>

      {/* Architecture note */}
      <Card title="How health affects trust">
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          {[
            ["HEALTHY (≥ 80)", "Full weight contribution. Nominal pass-through.", "#34d399"],
            ["WARNING (60–79)", "Reduced weight adjustment multiplier applied.", "#fbbf24"],
            ["DEGRADED (< 60)", "Significant weight reduction. Other models compensate.", "#f87171"],
          ].map(([label, desc, color]) => (
            <div key={label as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium mb-1" style={{ color: color as string }}>{label as string}</div>
              <div className="text-slate-400 text-xs">{desc as string}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Monitored signals: field completeness · run delay · value outlier rate · distribution shift · recent verification degradation.
          Thresholds are configurable — not official operational thresholds.
        </p>
      </Card>
    </Shell>
  );
}
