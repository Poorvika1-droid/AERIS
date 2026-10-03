"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import dynamic from "next/dynamic";
import { Shell, Card } from "@/components/shell";
import { apiGet } from "@/lib/api";

const IndiaMap = dynamic(() => import("@/components/india-map").then((m) => m.IndiaMap), { ssr: false });

const LAYER_OPTIONS = [
  { id: "value", label: "Forecast value", hint: "Blended AERIS forecast at selected variable / lead" },
  { id: "frs", label: "Reliability (FRS)", hint: "Forecast Reliability Score 0–100" },
  { id: "disagreement", label: "Model disagreement", hint: "0=agreement · 1=maximum inter-model spread" },
  { id: "risk", label: "Failure risk", hint: "LOW / MODERATE / HIGH decision-support indicator" },
  { id: "dominant", label: "Dominant model", hint: "Which model contributes most weight at each location" },
];

const RISK_COLORS: Record<string, string> = { HIGH: "#f87171", MODERATE: "#fbbf24", LOW: "#34d399" };
const MODEL_COLORS: Record<string, string> = {
  "nwp-mock-gfs-like": "#22d3ee",
  "ai-mock-emulator": "#34d399",
  "ens-mock-mean": "#a78bfa",
};

function rainColor(mm: number): string {
  if (mm > 60) return "#1d4ed8";
  if (mm > 30) return "#3b82f6";
  if (mm > 15) return "#60a5fa";
  if (mm > 5) return "#93c5fd";
  return "#22d3ee";
}
function tempColor(c: number): string {
  if (c > 42) return "#dc2626";
  if (c > 38) return "#f87171";
  if (c > 35) return "#fbbf24";
  if (c > 30) return "#fde68a";
  return "#34d399";
}
function windColor(ms: number): string {
  if (ms > 15) return "#7c3aed";
  if (ms > 10) return "#a78bfa";
  if (ms > 6) return "#c4b5fd";
  return "#22d3ee";
}
function frsColor(frs: number): string {
  if (frs >= 80) return "#34d399";
  if (frs >= 60) return "#fbbf24";
  return "#f87171";
}
function disagreementColor(d: number): string {
  if (d > 0.4) return "#f87171";
  if (d > 0.2) return "#fbbf24";
  return "#34d399";
}

export default function GisPage() {
  const [variable, setVariable] = useState("RAINFALL");
  const [lead, setLead] = useState(48);
  const [layer, setLayer] = useState("value");
  const [selectedPoint, setSelectedPoint] = useState<string | null>(null);

  const f = useQuery({
    queryKey: ["gis", variable, lead],
    queryFn: () =>
      apiGet<{
        items: Array<{
          location_id: string;
          name: string;
          lat: number;
          lon: number;
          value: number;
          frs: number;
          disagreement: number;
          failure_risk: string;
          dominant_model: string;
          weights: Record<string, number>;
          confidence: string;
          uncertainty_score: number;
        }>;
      }>(`/api/v1/forecast?variable=${variable}&lead_time_hours=${lead}`),
  });

  const points = (f.data?.items ?? []).map((p) => {
    let color = "#22d3ee";
    let extra = "";
    if (layer === "value") {
      color = variable === "RAINFALL" ? rainColor(p.value) : variable === "TEMPERATURE" ? tempColor(p.value) : windColor(p.value);
      extra = `${p.value?.toFixed?.(1)} ${variable === "RAINFALL" ? "mm" : variable === "TEMPERATURE" ? "°C" : "m/s"}`;
    } else if (layer === "frs") {
      color = frsColor(p.frs ?? 0);
      extra = `FRS ${p.frs ?? "—"}`;
    } else if (layer === "disagreement") {
      color = disagreementColor(p.disagreement ?? 0);
      extra = `Disagreement ${p.disagreement?.toFixed?.(3) ?? "—"}`;
    } else if (layer === "risk") {
      color = RISK_COLORS[p.failure_risk] ?? "#94a3b8";
      extra = p.failure_risk ?? "—";
    } else if (layer === "dominant") {
      color = MODEL_COLORS[p.dominant_model] ?? "#94a3b8";
      extra = p.dominant_model?.split("-")[0] ?? "—";
    }
    return {
      id: p.location_id,
      lat: p.lat,
      lon: p.lon,
      label: p.name,
      extra: `${extra} · ${p.name}`,
      color,
    };
  });

  const selected = f.data?.items?.find((p) => p.location_id === selectedPoint);

  const layerMeta = LAYER_OPTIONS.find((l) => l.id === layer);

  return (
    <Shell>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">India GIS</h1>
          <p className="mt-0.5 text-sm text-slate-400">
            {layerMeta?.hint ?? "Select a layer to explore spatial patterns."}
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Variable</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
          >
            <option>RAINFALL</option>
            <option>TEMPERATURE</option>
            <option>WIND_SPEED</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Lead time</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={lead}
            onChange={(e) => setLead(Number(e.target.value))}
          >
            {[6, 12, 24, 48, 72, 120].map((h) => <option key={h} value={h}>{h}h</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Layer</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={layer}
            onChange={(e) => setLayer(e.target.value)}
          >
            {LAYER_OPTIONS.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
          </select>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {/* Map — takes 3 cols */}
        <div className="lg:col-span-3">
          <Card>
            <IndiaMap points={points} onSelect={setSelectedPoint} />
            {/* Legend */}
            <div className="mt-3 flex flex-wrap gap-3 text-[11px]">
              {layer === "value" && variable === "RAINFALL" && [
                ["< 5 mm", "#22d3ee"], ["5–15 mm", "#93c5fd"], ["15–30 mm", "#60a5fa"],
                ["30–60 mm", "#3b82f6"], ["> 60 mm", "#1d4ed8"],
              ].map(([label, color]) => (
                <div key={label as string} className="flex items-center gap-1.5 text-slate-400">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: color as string }} />
                  {label as string}
                </div>
              ))}
              {layer === "frs" && [
                ["≥ 80 HIGH", "#34d399"], ["60–79 MODERATE", "#fbbf24"], ["< 60 LOW", "#f87171"],
              ].map(([label, color]) => (
                <div key={label as string} className="flex items-center gap-1.5 text-slate-400">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: color as string }} />
                  {label as string}
                </div>
              ))}
              {layer === "disagreement" && [
                ["< 0.2 LOW", "#34d399"], ["0.2–0.4 MOD", "#fbbf24"], ["> 0.4 HIGH", "#f87171"],
              ].map(([label, color]) => (
                <div key={label as string} className="flex items-center gap-1.5 text-slate-400">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: color as string }} />
                  {label as string}
                </div>
              ))}
              {layer === "risk" && Object.entries(RISK_COLORS).map(([r, c]) => (
                <div key={r} className="flex items-center gap-1.5 text-slate-400">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
                  {r}
                </div>
              ))}
              {layer === "dominant" && Object.entries(MODEL_COLORS).map(([m, c]) => (
                <div key={m} className="flex items-center gap-1.5 text-slate-400">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />
                  {m.split("-")[0]}
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Location detail panel */}
        <div className="space-y-3">
          <Card title="Location detail">
            {selected ? (
              <div className="space-y-2 text-sm">
                <div className="font-semibold text-white">{selected.name}</div>
                <div className="text-slate-400 text-xs">{selected.location_id}</div>
                <div className="h-px bg-white/5" />
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Value</span>
                    <span className="text-white font-mono">{selected.value?.toFixed?.(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">FRS</span>
                    <span style={{ color: frsColor(selected.frs ?? 0) }}>{selected.frs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Disagreement</span>
                    <span style={{ color: disagreementColor(selected.disagreement ?? 0) }}>
                      {selected.disagreement?.toFixed?.(3)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Failure risk</span>
                    <span style={{ color: RISK_COLORS[selected.failure_risk] ?? "#94a3b8" }}>
                      {selected.failure_risk}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Dominant</span>
                    <span style={{ color: MODEL_COLORS[selected.dominant_model] ?? "#94a3b8" }}>
                      {selected.dominant_model?.split("-")[0]}
                    </span>
                  </div>
                </div>
                {selected.weights && (
                  <>
                    <div className="h-px bg-white/5" />
                    <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1">Trust weights</div>
                    {Object.entries(selected.weights).map(([m, w]) => (
                      <div key={m}>
                        <div className="flex justify-between text-[11px] mb-0.5">
                          <span style={{ color: MODEL_COLORS[m] ?? "#94a3b8" }}>{m.split("-")[0]}</span>
                          <span className="text-white">{(w * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 rounded bg-navy-700">
                          <div className="h-1 rounded" style={{ width: `${w * 100}%`, background: MODEL_COLORS[m] ?? "#22d3ee" }} />
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Click a point on the map to see details.</p>
            )}
          </Card>

          <Card title="Layer stats">
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Locations</span>
                <span className="text-white">{f.data?.items?.length ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Variable</span>
                <span className="text-white">{variable}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Lead time</span>
                <span className="text-white">{lead}h</span>
              </div>
              {f.data?.items && (
                <>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Avg FRS</span>
                    <span className="text-white">
                      {(f.data.items.reduce((s, p) => s + (p.frs ?? 0), 0) / f.data.items.length).toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">High-risk locations</span>
                    <span className="text-red-400">
                      {f.data.items.filter((p) => p.failure_risk === "HIGH").length}
                    </span>
                  </div>
                </>
              )}
            </div>
          </Card>
        </div>
      </div>
    </Shell>
  );
}
