"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
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
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const VARS = ["RAINFALL", "TEMPERATURE", "WIND_SPEED"];
const MODEL_COLORS: Record<string, string> = {
  "nwp-mock-gfs-like": "#22d3ee",
  "ai-mock-emulator": "#34d399",
  "ens-mock-mean": "#a78bfa",
  "aeris-blend": "#f59e0b",
  "static-equal": "#94a3b8",
};
const MODEL_LABELS: Record<string, string> = {
  "nwp-mock-gfs-like": "NWP",
  "ai-mock-emulator": "AI",
  "ens-mock-mean": "Ensemble",
  "aeris-blend": "AERIS blend",
  "static-equal": "Static equal weight",
};

type VerRow = {
  model_id: string;
  variable: string;
  region: string;
  mae: number;
  rmse: number;
  bias: number;
  crps: number | null;
  brier: number | null;
  csi: number | null;
  f1: number | null;
  precision: number | null;
  recall: number | null;
  n: number;
  note: string;
};

type SkillByLead = {
  data: Record<string, Array<{ lead: number; mae: number; rmse: number }>>;
};

export default function VerificationPage() {
  const [variable, setVariable] = useState("RAINFALL");

  const q = useQuery({
    queryKey: ["ver"],
    queryFn: () => apiGet<{ label: string; items: VerRow[] }>("/api/v1/verification"),
  });
  const byLead = useQuery({
    queryKey: ["vbl", variable],
    queryFn: () => apiGet<SkillByLead>(`/api/v1/verification/by-lead?variable=${variable}`),
  });

  const rows = (q.data?.items ?? []).filter((r) => r.variable === variable);

  // MAE bar chart data
  const maeData = rows.map((r) => ({
    name: MODEL_LABELS[r.model_id] ?? r.model_id,
    MAE: parseFloat(r.mae?.toFixed?.(3) ?? "0"),
    RMSE: parseFloat(r.rmse?.toFixed?.(3) ?? "0"),
    Bias: parseFloat(Math.abs(r.bias ?? 0).toFixed?.(3) ?? "0"),
    color: MODEL_COLORS[r.model_id] ?? "#94a3b8",
  }));

  // Skill-by-lead line chart
  const leadData = (() => {
    const d = byLead.data?.data ?? {};
    const leads = [6, 12, 24, 48, 72, 120];
    return leads.map((l) => {
      const pt: Record<string, string | number> = { lead: `${l}h` };
      Object.entries(d).forEach(([m, pts]) => {
        const match = (pts ?? []).find((p) => p.lead === l);
        if (match) pt[MODEL_LABELS[m] ?? m] = parseFloat(match.mae.toFixed(3));
      });
      return pt;
    });
  })();

  // Radar chart — multi-metric for first few models
  const radarModels = rows.filter((r) => r.csi != null || r.brier != null);
  const radarData = [
    { metric: "MAE↓", ...Object.fromEntries(radarModels.map((r) => [MODEL_LABELS[r.model_id] ?? r.model_id, Math.max(0, 1 - (r.mae ?? 0) / 5)])) },
    { metric: "RMSE↓", ...Object.fromEntries(radarModels.map((r) => [MODEL_LABELS[r.model_id] ?? r.model_id, Math.max(0, 1 - (r.rmse ?? 0) / 7)])) },
    { metric: "CSI↑", ...Object.fromEntries(radarModels.map((r) => [MODEL_LABELS[r.model_id] ?? r.model_id, r.csi ?? 0])) },
    { metric: "Precision↑", ...Object.fromEntries(radarModels.map((r) => [MODEL_LABELS[r.model_id] ?? r.model_id, r.precision ?? 0])) },
    { metric: "Recall↑", ...Object.fromEntries(radarModels.map((r) => [MODEL_LABELS[r.model_id] ?? r.model_id, r.recall ?? 0])) },
    { metric: "|Bias|↓", ...Object.fromEntries(radarModels.map((r) => [MODEL_LABELS[r.model_id] ?? r.model_id, Math.max(0, 1 - Math.abs(r.bias ?? 0) / 3)])) },
  ];

  return (
    <Shell>
      <div className="mb-4 rounded border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-100">
        <strong>DEMONSTRATION BENCHMARK</strong> — generated from seeded synthetic ensembles with controlled error hierarchy.
        Not operational NCMRWF forecast accuracy. Results are reproducible and deterministic.
      </div>

      <div className="mb-4 flex items-end justify-between">
        <h1 className="text-2xl font-semibold text-white">Verification</h1>
        <div className="flex gap-2">
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
          >
            {VARS.map((v) => <option key={v}>{v}</option>)}
          </select>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        {/* MAE / RMSE Bar chart */}
        <Card title={`MAE & RMSE by source — ${variable}`}>
          {maeData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={maeData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="MAE" fill="#22d3ee" radius={[3, 3, 0, 0]}>
                    {maeData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                  </Bar>
                  <Bar dataKey="RMSE" fill="#34d399" fillOpacity={0.6} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-500 text-sm">Seed demo data first.</div>
          )}
        </Card>

        {/* MAE vs lead time */}
        <Card title={`MAE vs lead time — ${variable} (skill degradation)`}>
          {leadData.some((d) => Object.keys(d).length > 1) ? (
            <div className="h-64">
              <ResponsiveContainer>
                <LineChart data={leadData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="lead" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="NWP" stroke="#22d3ee" dot={true} strokeWidth={2} />
                  <Line type="monotone" dataKey="AI" stroke="#34d399" dot={true} strokeWidth={2} />
                  <Line type="monotone" dataKey="Ensemble" stroke="#a78bfa" dot={true} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-500 text-sm">Seed demo data first.</div>
          )}
        </Card>
      </div>

      {/* Radar chart */}
      {radarData[0] && Object.keys(radarData[0]).length > 1 && (
        <Card title="Multi-metric skill radar (normalised, higher = better)" className="mb-4">
          <div className="h-72">
            <ResponsiveContainer>
              <RadarChart data={radarData} margin={{ top: 8, right: 24, left: 24, bottom: 8 }}>
                <PolarGrid stroke="#1e293b" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <PolarRadiusAxis tick={{ fill: "#64748b", fontSize: 9 }} domain={[0, 1]} />
                {radarModels.map((r) => (
                  <Radar
                    key={r.model_id}
                    name={MODEL_LABELS[r.model_id] ?? r.model_id}
                    dataKey={MODEL_LABELS[r.model_id] ?? r.model_id}
                    stroke={MODEL_COLORS[r.model_id] ?? "#94a3b8"}
                    fill={MODEL_COLORS[r.model_id] ?? "#94a3b8"}
                    fillOpacity={0.12}
                    strokeWidth={2}
                  />
                ))}
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">↑ = higher is better (MAE/RMSE/|Bias| are inverted). DEMONSTRATION BENCHMARK only.</p>
        </Card>
      )}

      {/* Full metrics table */}
      <Card title="Full metrics table">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-white/10">
                <th className="pb-2 pr-3">Model</th>
                <th className="pb-2 pr-3">Var</th>
                <th className="pb-2 pr-3">MAE</th>
                <th className="pb-2 pr-3">RMSE</th>
                <th className="pb-2 pr-3">Bias</th>
                <th className="pb-2 pr-3">CRPS</th>
                <th className="pb-2 pr-3">Brier</th>
                <th className="pb-2 pr-3">CSI</th>
                <th className="pb-2 pr-3">F1</th>
                <th className="pb-2 pr-3">n</th>
              </tr>
            </thead>
            <tbody>
              {(q.data?.items ?? []).map((r, i) => (
                <tr key={i} className="border-t border-white/5 hover:bg-white/2">
                  <td className="py-1.5 pr-3" style={{ color: MODEL_COLORS[r.model_id] ?? "#94a3b8" }}>
                    {MODEL_LABELS[r.model_id] ?? r.model_id}
                  </td>
                  <td className="py-1.5 pr-3 text-slate-400">{r.variable}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.mae?.toFixed?.(3)}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.rmse?.toFixed?.(3)}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.bias?.toFixed?.(3)}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.crps?.toFixed?.(3) ?? "—"}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.brier?.toFixed?.(3) ?? "—"}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.csi?.toFixed?.(3) ?? "—"}</td>
                  <td className="py-1.5 pr-3 font-mono">{r.f1?.toFixed?.(3) ?? "—"}</td>
                  <td className="py-1.5 font-mono text-slate-400">{r.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          AERIS blend vs static equal-weight demonstrates the adaptive advantage.
          All numbers are from deterministic seeded benchmark data — not real operational archives.
        </p>
      </Card>
    </Shell>
  );
}
