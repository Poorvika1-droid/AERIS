"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { Shell, Card } from "@/components/shell";
import { apiGet } from "@/lib/api";
import {
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

const REGIME_COLORS: Record<string, string> = {
  NORMAL: "#64748b",
  MONSOON: "#38bdf8",
  CONVECTIVE_RAIN: "#818cf8",
  HEAVY_RAIN: "#3b82f6",
  HEATWAVE: "#fb7185",
  HIGH_WIND: "#fbbf24",
  CYCLONIC_INFLUENCE: "#a78bfa",
  DRY_EXTREME: "#f97316",
  TRANSITION: "#94a3b8",
};

type RegimeItem = {
  location_id: string;
  name: string;
  lat: number;
  lon: number;
  current_regime: string;
  previous_regime: string | null;
  transition_probability: number;
  transition_confidence: number;
  features: Record<string, number>;
};

export default function RegimesPage() {
  const q = useQuery({
    queryKey: ["rg"],
    queryFn: () =>
      apiGet<{ note: string; items: RegimeItem[] }>("/api/v1/regimes"),
  });

  const items = q.data?.items ?? [];

  const mapPoints = items.map((p) => ({
    id: p.location_id,
    lat: p.lat,
    lon: p.lon,
    label: p.name,
    extra: `${p.current_regime} · P(transition)=${(p.transition_probability * 100).toFixed(0)}%`,
    color: REGIME_COLORS[p.current_regime] ?? "#22d3ee",
  }));

  // Regime distribution pie
  const regimeCounts = items.reduce<Record<string, number>>((acc, p) => {
    acc[p.current_regime] = (acc[p.current_regime] ?? 0) + 1;
    return acc;
  }, {});
  const pieData = Object.entries(regimeCounts).map(([r, n]) => ({
    name: r,
    value: n,
    color: REGIME_COLORS[r] ?? "#94a3b8",
  }));

  // Transition probability bar chart
  const transData = items
    .filter((p) => p.transition_probability > 0.2)
    .sort((a, b) => b.transition_probability - a.transition_probability)
    .slice(0, 12)
    .map((p) => ({
      name: p.name.slice(0, 12),
      prob: parseFloat((p.transition_probability * 100).toFixed(1)),
      confidence: parseFloat((p.transition_confidence * 100).toFixed(1)),
      regime: p.current_regime,
    }));

  return (
    <Shell>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-white">Weather regimes</h1>
        <p className="mt-1 text-sm text-slate-400 max-w-3xl">
          {q.data?.note ??
            "Operational regime classes for adaptive model weighting — not official meteorological classifications."}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3 mb-4">
        {/* Map */}
        <Card title="Current regime map — India" className="lg:col-span-2">
          <div className="mb-3 flex flex-wrap gap-2">
            {Object.entries(REGIME_COLORS).map(([r, c]) => (
              <div key={r} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <div className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
                {r}
              </div>
            ))}
          </div>
          <IndiaMap points={mapPoints} />
        </Card>

        {/* Regime distribution pie */}
        <Card title="Regime distribution">
          {pieData.length > 0 ? (
            <>
              <div className="h-52">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={65}
                      label={({ name, value }) => `${name.slice(0, 8)} ${value}`}
                      labelLine={false}
                      fontSize={10}
                    >
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 space-y-1">
                {pieData.map((d) => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="h-2 w-2 rounded-full" style={{ background: d.color }} />
                      <span className="text-slate-400">{d.name}</span>
                    </div>
                    <span className="font-mono text-slate-300">{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">
              Seed demo data first.
            </div>
          )}
        </Card>
      </div>

      {/* Transition probability */}
      <Card title="Regime transition probability — top locations" className="mb-4">
        {transData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={transData} layout="vertical" margin={{ top: 4, right: 32, left: 72, bottom: 0 }}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={11} domain={[0, 100]} unit="%" />
                <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={70} />
                <Tooltip
                  contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                  formatter={(v: number, k: string) => [`${v}%`, k]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="prob" name="Transition probability" radius={[0, 3, 3, 0]}>
                  {transData.map((entry) => (
                    <Cell key={entry.name} fill={REGIME_COLORS[entry.regime] ?? "#22d3ee"} />
                  ))}
                </Bar>
                <Bar dataKey="confidence" name="Confidence" fill="#475569" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
            No transitions above threshold.
          </div>
        )}
        <p className="mt-2 text-[11px] text-slate-500">
          High transition probability → ensemble weight boosted; regime uncertainty → FRS reduced.
        </p>
      </Card>

      {/* Regime explanations */}
      <Card title="Operational regime classes (weighting rationale)">
        <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["NORMAL", "Low anomalies; NWP and ensemble weights nominal."],
            ["MONSOON", "Active Jun–Sep; NWP skill elevated for large-scale pattern."],
            ["CONVECTIVE_RAIN", "Short-lead AI weight boosted; NWP convective penalty."],
            ["HEAVY_RAIN", "Extreme objective engaged; CSI and Brier score prioritized."],
            ["HEATWAVE", "Temperature MAE objective; temperature threshold configurable."],
            ["HIGH_WIND", "Wind event detection; high-wind CSI in blending objective."],
            ["CYCLONIC_INFLUENCE", "Low-pressure detected; NWP synoptic skill elevated."],
            ["DRY_EXTREME", "Dry spell; rainfall threshold suppressed."],
            ["TRANSITION", "Ensemble weight boosted ×1.15; FRS regime certainty reduced."],
          ].map(([name, desc]) => (
            <div key={name as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium mb-0.5 flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full" style={{ background: REGIME_COLORS[name as string] ?? "#94a3b8" }} />
                <span style={{ color: REGIME_COLORS[name as string] ?? "#94a3b8" }}>{name as string}</span>
              </div>
              <div className="text-slate-400">{desc as string}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          These are prototype operational classes for adaptive weighting — not official IMD/NCMRWF classifications.
          Future work: transformer-based regime encoder for higher resolution labels.
        </p>
      </Card>
    </Shell>
  );
}
