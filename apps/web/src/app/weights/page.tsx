"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import dynamic from "next/dynamic";
import { Shell, Card } from "@/components/shell";
import { apiGet } from "@/lib/api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const IndiaMap = dynamic(() => import("@/components/india-map").then((m) => m.IndiaMap), { ssr: false });

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

type WeightItem = {
  location_id: string;
  name: string;
  lat: number;
  lon: number;
  weights: Record<string, number>;
  dominant: string;
  regime: string;
  forecast_id: string;
};

type WeightHistory = {
  series: Array<Record<string, number | string>>;
};

export default function WeightsPage() {
  const [variable, setVariable] = useState("RAINFALL");
  const [lead, setLead] = useState(48);
  const [dominantFilter, setDominantFilter] = useState<string>("");
  const [selectedLoc, setSelectedLoc] = useState<string | null>(null);
  const [histLoc, setHistLoc] = useState("IN-DL-DEL");

  const w = useQuery({
    queryKey: ["w", variable, lead],
    queryFn: () =>
      apiGet<{ items: WeightItem[] }>(
        `/api/v1/weights?variable=${variable}&lead_time_hours=${lead}`,
      ),
  });

  const hist = useQuery({
    queryKey: ["wh", histLoc, variable],
    queryFn: () =>
      apiGet<WeightHistory>(
        `/api/v1/weights/history?location_id=${histLoc}&variable=${variable}`,
      ),
  });

  const items = (w.data?.items ?? []).filter((p) =>
    dominantFilter ? p.dominant?.startsWith(dominantFilter) : true,
  );

  const points = items.map((p) => ({
    id: p.location_id,
    lat: p.lat,
    lon: p.lon,
    label: p.name,
    extra: [
      ...Object.entries(p.weights ?? {}).map(([m, wv]) => `${m.split("-")[0]} ${(wv * 100).toFixed(0)}%`),
      p.regime,
    ].join(" · "),
    color: MODEL_COLORS[p.dominant] ?? "#94a3b8",
  }));

  // Average weights by dominant model
  const avgByDom: Record<string, { nwp: number; ai: number; ens: number; count: number }> = {};
  for (const p of w.data?.items ?? []) {
    const dom = p.dominant?.split("-")[0] ?? "unknown";
    if (!avgByDom[dom]) avgByDom[dom] = { nwp: 0, ai: 0, ens: 0, count: 0 };
    for (const [m, wv] of Object.entries(p.weights ?? {})) {
      const short = m.split("-")[0];
      if (short in avgByDom[dom]) (avgByDom[dom] as Record<string, number>)[short] += wv;
    }
    avgByDom[dom].count++;
  }
  const domChart = Object.entries(avgByDom).map(([dom, v]) => ({
    dominant: dom,
    NWP: parseFloat(((v.nwp / v.count) * 100).toFixed(1)),
    AI: parseFloat(((v.ai / v.count) * 100).toFixed(1)),
    Ensemble: parseFloat(((v.ens / v.count) * 100).toFixed(1)),
    locations: v.count,
  }));

  // Weight evolution
  const wSeries = hist.data?.series ?? [];
  const selectedItem = w.data?.items?.find((p) => p.location_id === selectedLoc);

  const CITY_OPTIONS = [
    { id: "IN-DL-DEL", name: "New Delhi" },
    { id: "IN-MH-MUM", name: "Mumbai" },
    { id: "IN-WB-KOL", name: "Kolkata" },
    { id: "IN-TN-CHE", name: "Chennai" },
    { id: "IN-AS-GHY", name: "Guwahati" },
  ];

  return (
    <Shell>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-white">Model weight maps</h1>
        <p className="mt-0.5 text-sm text-slate-400">
          Spatially smoothed, context-aware trust weights. Cyan = NWP dominant · Green = AI dominant · Violet = ensemble dominant.
        </p>
      </div>

      {/* Controls */}
      <div className="mb-4 flex flex-wrap gap-3">
        {[
          ["Variable", variable, (v: string) => setVariable(v), ["RAINFALL", "TEMPERATURE", "WIND_SPEED"]],
          ["Lead time", String(lead), (v: string) => setLead(Number(v)), ["6", "12", "24", "48", "72", "120"]],
        ].map(([label, value, setter, opts]) => (
          <div key={label as string} className="flex flex-col gap-1">
            <label className="text-[11px] uppercase tracking-wider text-slate-500">{label as string}</label>
            <select
              className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
              value={value as string}
              onChange={(e) => (setter as (v: string) => void)(e.target.value)}
            >
              {(opts as string[]).map((o) => <option key={o} value={o}>{o}{label === "Lead time" ? "h" : ""}</option>)}
            </select>
          </div>
        ))}
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Dominant filter</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={dominantFilter}
            onChange={(e) => setDominantFilter(e.target.value)}
          >
            <option value="">All models</option>
            <option value="nwp">NWP dominant</option>
            <option value="ai">AI dominant</option>
            <option value="ens">Ensemble dominant</option>
          </select>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4 mb-4">
        {/* Map */}
        <div className="lg:col-span-3">
          <Card title="Dominant model trust map">
            <div className="mb-2 flex gap-4 text-[11px]">
              {Object.entries(MODEL_COLORS).map(([m, c]) => (
                <div key={m} className="flex items-center gap-1.5 text-slate-400">
                  <div className="h-2 w-2 rounded-full" style={{ background: c }} />
                  {MODEL_LABELS[m]}
                </div>
              ))}
            </div>
            <IndiaMap points={points} onSelect={setSelectedLoc} />
            <p className="mt-2 text-[11px] text-slate-500">
              Spatial smoothing (MEDIUM) applied. Weights are geographically coherent without over-smoothing extremes.
            </p>
          </Card>
        </div>

        {/* Location detail */}
        <Card title="Location weights">
          {selectedItem ? (
            <div className="space-y-2 text-sm">
              <div className="font-semibold text-white">{selectedItem.name}</div>
              <div className="text-xs text-slate-400">{selectedItem.regime} (operational class)</div>
              <div className="h-px bg-white/5" />
              {Object.entries(selectedItem.weights ?? {}).map(([m, wv]) => (
                <div key={m}>
                  <div className="flex justify-between text-xs mb-0.5">
                    <span style={{ color: MODEL_COLORS[m] ?? "#94a3b8" }}>{MODEL_LABELS[m] ?? m}</span>
                    <span className="font-semibold text-white">{(wv * 100).toFixed(1)}%</span>
                  </div>
                  <div className="h-2 rounded bg-navy-700">
                    <div
                      className="h-2 rounded"
                      style={{ width: `${wv * 100}%`, background: MODEL_COLORS[m] ?? "#22d3ee" }}
                    />
                  </div>
                </div>
              ))}
              <div className="text-[11px] text-slate-500 mt-2">
                Weights always ≥ 0 and sum to 1.
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Click a map point to see weights.</p>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        {/* Average weights by dominant model type */}
        <Card title="Average weight distribution by dominant region">
          {domChart.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <BarChart data={domChart} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="dominant" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                    formatter={(v: number) => `${v}%`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="NWP" fill="#22d3ee" stackId="s" />
                  <Bar dataKey="AI" fill="#34d399" stackId="s" />
                  <Bar dataKey="Ensemble" fill="#a78bfa" stackId="s" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
        </Card>

        {/* Weight evolution over lead times */}
        <Card title="Weight evolution — select city">
          <div className="flex items-center gap-2 mb-3">
            <select
              className="rounded border border-cyan-900/40 bg-navy-900 px-2 py-1 text-sm text-slate-200"
              value={histLoc}
              onChange={(e) => setHistLoc(e.target.value)}
            >
              {CITY_OPTIONS.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {wSeries.length > 0 ? (
            <div className="h-40">
              <ResponsiveContainer>
                <LineChart data={wSeries} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="lead" stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `${v}h`} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} unit="%" />
                  <Tooltip
                    contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                    formatter={(v: number) => `${v?.toFixed?.(1)}%`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="nwp" stroke="#22d3ee" strokeWidth={2} dot={true} name="NWP" />
                  <Line type="monotone" dataKey="ai" stroke="#34d399" strokeWidth={2} dot={true} name="AI" />
                  <Line type="monotone" dataKey="ens" stroke="#a78bfa" strokeWidth={2} dot={true} name="Ensemble" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            Dynamic trust engine: weights shift as lead time changes based on historical skill differences.
          </p>
        </Card>
      </div>

      {/* Stats */}
      <Card title="Spatial statistics">
        <div className="grid gap-2 text-xs sm:grid-cols-3">
          {Object.entries(MODEL_COLORS).map(([m]) => {
            const dom = w.data?.items?.filter((p) => p.dominant === m).length ?? 0;
            const pct = w.data?.items?.length ? ((dom / w.data.items.length) * 100).toFixed(0) : "—";
            const avg = w.data?.items
              ? (w.data.items.reduce((s, p) => s + (p.weights[m] ?? 0), 0) / w.data.items.length * 100).toFixed(1)
              : "—";
            return (
              <div key={m} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
                <div className="font-medium mb-1" style={{ color: MODEL_COLORS[m] }}>
                  {MODEL_LABELS[m]}
                </div>
                <div className="text-slate-400">Dominant at <span className="text-white">{pct}%</span> of locations</div>
                <div className="text-slate-400">Mean weight: <span className="text-white">{avg}%</span></div>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          Spatial smoothing (MEDIUM) maintains geographic coherence without suppressing extreme-event signals.
        </p>
      </Card>
    </Shell>
  );
}
