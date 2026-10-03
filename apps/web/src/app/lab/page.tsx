"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Shell, Card } from "@/components/shell";
import { apiGet, apiPost } from "@/lib/api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
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

const CITY_OPTIONS = [
  { id: "IN-DL-DEL", name: "New Delhi" },
  { id: "IN-MH-MUM", name: "Mumbai" },
  { id: "IN-WB-KOL", name: "Kolkata" },
  { id: "IN-TN-CHE", name: "Chennai" },
  { id: "IN-KA-BLR", name: "Bengaluru" },
  { id: "IN-AS-GHY", name: "Guwahati" },
];

const MODEL_IDS = ["nwp-mock-gfs-like", "ai-mock-emulator", "ens-mock-mean"] as const;
const MODEL_LABELS: Record<string, string> = {
  "nwp-mock-gfs-like": "NWP",
  "ai-mock-emulator": "AI",
  "ens-mock-mean": "Ensemble",
};
const MODEL_COLORS: Record<string, string> = {
  "nwp-mock-gfs-like": "#22d3ee",
  "ai-mock-emulator": "#34d399",
  "ens-mock-mean": "#a78bfa",
};
const STRATEGIES = ["CONTEXTUAL_ML", "SKILL_WEIGHTED", "BAYESIAN_AVERAGE", "OPTIMIZATION", "EVENT_SPECIFIC"];

type ForecastDetail = {
  forecast_id: string;
  value: number;
  weights: Record<string, number>;
  uncertainty: {
    frs: number;
    frs_label: string;
    disagreement: number;
    disagreement_label: string;
    uncertainty_score: number;
    failure_risk: string;
  } | null;
};

type SimResult = {
  simulation: boolean;
  label: string;
  baseline_forecast: number;
  scenario_forecast: number;
  forecast_delta: number;
  baseline_weights: Record<string, number>;
  scenario_weights: Record<string, number>;
  uncertainty_delta: number;
  baseline_uncertainty: number;
  scenario_uncertainty: number;
  production_mutated: boolean;
  simulation_id: string;
};

export default function LabPage() {
  const [loc, setLoc] = useState("IN-DL-DEL");
  const [variable, setVariable] = useState("RAINFALL");
  const [lead, setLead] = useState(48);
  const [removeModels, setRemoveModels] = useState<string[]>([]);
  const [boosts, setBoosts] = useState<Record<string, number>>({});
  const [strategy, setStrategy] = useState<string>("");

  const f = useQuery({
    queryKey: ["labf", loc, variable, lead],
    queryFn: () =>
      apiGet<ForecastDetail>(
        `/api/v1/forecast?location_id=${loc}&variable=${variable}&lead_time_hours=${lead}`,
      ),
    retry: false,
  });

  const sim = useMutation({
    mutationFn: () =>
      apiPost<SimResult>("/api/v1/simulations/counterfactual", {
        forecast_id: f.data?.forecast_id,
        location_id: loc,
        variable,
        lead_time_hours: lead,
        remove_models: removeModels,
        simulate_outage: removeModels,
        weight_boosts: Object.fromEntries(
          Object.entries(boosts).filter(([, v]) => v !== 0),
        ),
        strategy: strategy || null,
      }),
  });

  const r = sim.data;
  const u = f.data?.uncertainty;

  // Weight comparison chart
  const wBaseData = Object.entries(f.data?.weights ?? {}).map(([m, w]) => ({
    model: MODEL_LABELS[m] ?? m,
    Baseline: parseFloat((w * 100).toFixed(1)),
    Scenario: r ? parseFloat(((r.scenario_weights[m] ?? 0) * 100).toFixed(1)) : 0,
    color: MODEL_COLORS[m] ?? "#94a3b8",
  }));

  const deltaColor = (d?: number) =>
    d == null ? "#94a3b8" : Math.abs(d) < 0.1 ? "#34d399" : d > 0 ? "#fbbf24" : "#f87171";

  return (
    <Shell>
      <div className="mb-2 flex items-center gap-2">
        <div className="rounded bg-amber-500/20 px-3 py-1 text-xs font-bold text-amber-200 border border-amber-500/40">
          SIMULATION MODE
        </div>
        <span className="text-xs text-slate-500">Production weights are never mutated by this tool.</span>
      </div>

      <h1 className="mb-1 text-2xl font-semibold text-white">Counterfactual Lab</h1>
      <p className="mb-5 text-sm text-slate-400">
        "What if a model is unavailable?" · "What if AI contributes more?" · All results are purely hypothetical.
      </p>

      {/* Controls */}
      <div className="grid gap-4 lg:grid-cols-2 mb-5">
        <Card title="Scenario configuration">
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] uppercase tracking-wider text-slate-500">Location</label>
                <select
                  className="rounded border border-cyan-900/40 bg-navy-900 px-2 py-1.5 text-sm text-slate-200"
                  value={loc}
                  onChange={(e) => setLoc(e.target.value)}
                >
                  {CITY_OPTIONS.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[11px] uppercase tracking-wider text-slate-500">Variable</label>
                <select
                  className="rounded border border-cyan-900/40 bg-navy-900 px-2 py-1.5 text-sm text-slate-200"
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
                  className="rounded border border-cyan-900/40 bg-navy-900 px-2 py-1.5 text-sm text-slate-200"
                  value={lead}
                  onChange={(e) => setLead(Number(e.target.value))}
                >
                  {[6, 12, 24, 48, 72, 120].map((h) => <option key={h} value={h}>{h}h</option>)}
                </select>
              </div>
            </div>

            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">Remove / simulate outage</div>
              <div className="flex flex-wrap gap-2">
                {MODEL_IDS.map((m) => (
                  <button
                    key={m}
                    onClick={() =>
                      setRemoveModels((prev) =>
                        prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m],
                      )
                    }
                    className={`rounded px-3 py-1.5 text-xs transition-all ${
                      removeModels.includes(m)
                        ? "bg-red-500/25 text-red-300 border border-red-500/60"
                        : "border border-white/10 text-slate-400 hover:border-cyan-500/40 hover:text-slate-200"
                    }`}
                  >
                    {removeModels.includes(m) ? "✗ " : "+ "}{MODEL_LABELS[m]}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">Weight boost / penalty (fractional, e.g. 0.3 = +30%)</div>
              <div className="grid grid-cols-3 gap-2">
                {MODEL_IDS.map((m) => (
                  <div key={m} className="flex flex-col gap-1">
                    <label className="text-[11px]" style={{ color: MODEL_COLORS[m] }}>{MODEL_LABELS[m]}</label>
                    <input
                      type="number"
                      step="0.1"
                      min="-0.9"
                      max="2"
                      className="rounded border border-cyan-900/40 bg-navy-900 px-2 py-1 text-sm text-slate-200"
                      value={boosts[m] ?? 0}
                      onChange={(e) => setBoosts((b) => ({ ...b, [m]: Number(e.target.value) }))}
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] uppercase tracking-wider text-slate-500">Blending strategy override (optional)</label>
              <select
                className="rounded border border-cyan-900/40 bg-navy-900 px-2 py-1.5 text-sm text-slate-200"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
              >
                <option value="">— Use default (CONTEXTUAL_ML) —</option>
                {STRATEGIES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>

            <button
              onClick={() => sim.mutate()}
              disabled={sim.isPending || !f.data?.forecast_id}
              className="w-full rounded bg-cyan-500 px-4 py-2 text-sm font-semibold text-navy-950 hover:bg-cyan-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sim.isPending ? "Running simulation…" : "Run counterfactual simulation"}
            </button>
            {!f.data?.forecast_id && (
              <p className="text-xs text-amber-300">Seed demo data from Overview page first.</p>
            )}
          </div>
        </Card>

        {/* Baseline state */}
        <Card title="Production baseline (read-only)">
          {f.data ? (
            <div className="space-y-3">
              <div>
                <div className="text-3xl font-semibold text-white">
                  {f.data.value.toFixed(1)} <span className="text-lg text-slate-400">mm</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">Forecast ID: {f.data.forecast_id}</div>
              </div>
              <div className="space-y-1.5">
                {Object.entries(f.data.weights).map(([m, w]) => (
                  <div key={m}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span style={{ color: MODEL_COLORS[m] ?? "#94a3b8" }}>{MODEL_LABELS[m] ?? m}</span>
                      <span className="text-white font-mono">{(w * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 rounded bg-navy-700">
                      <div className="h-1.5 rounded" style={{ width: `${w * 100}%`, background: MODEL_COLORS[m] ?? "#22d3ee" }} />
                    </div>
                  </div>
                ))}
              </div>
              {u && (
                <div className="rounded bg-navy-700/60 px-3 py-2 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-400">FRS</span>
                    <span className="text-white">{u.frs} — {u.frs_label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Disagreement</span>
                    <span className="text-white">{u.disagreement_label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Failure risk</span>
                    <span className="text-white">{u.failure_risk}</span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500 text-sm">Load data first.</div>
          )}
        </Card>
      </div>

      {/* Simulation results */}
      {r && (
        <>
          <div className="mb-2 flex items-center gap-2">
            <div className="rounded bg-amber-500/20 px-3 py-1 text-xs font-bold text-amber-200 border border-amber-500/40">
              {r.label}
            </div>
            <span className="text-xs text-slate-500">
              sim_id={r.simulation_id} · production_mutated={String(r.production_mutated)}
            </span>
          </div>

          <div className="grid gap-4 lg:grid-cols-3 mb-4">
            <Card title="Baseline">
              <div className="text-3xl font-semibold text-white">{r.baseline_forecast.toFixed(2)}</div>
              <div className="text-sm text-slate-400 mt-1">Uncertainty: {r.baseline_uncertainty.toFixed(3)}</div>
            </Card>
            <Card title="Scenario (SIMULATION)">
              <div className="text-3xl font-semibold text-cyan-300">{r.scenario_forecast.toFixed(2)}</div>
              <div className="text-sm text-slate-400 mt-1">Uncertainty: {r.scenario_uncertainty.toFixed(3)}</div>
            </Card>
            <Card title="Delta">
              <div className="text-3xl font-semibold" style={{ color: deltaColor(r.forecast_delta) }}>
                {r.forecast_delta >= 0 ? "+" : ""}{r.forecast_delta.toFixed(2)}
              </div>
              <div className="text-sm mt-1" style={{ color: deltaColor(r.uncertainty_delta) }}>
                Uncertainty Δ: {r.uncertainty_delta >= 0 ? "+" : ""}{r.uncertainty_delta.toFixed(3)}
              </div>
            </Card>
          </div>

          {/* Weight comparison */}
          <Card title="Weight comparison — baseline vs scenario">
            {wBaseData.length > 0 && (
              <div className="h-48">
                <ResponsiveContainer>
                  <BarChart data={wBaseData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="model" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} unit="%" />
                    <Tooltip
                      contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                      formatter={(v: number) => `${v}%`}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Baseline" fill="#475569" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="Scenario" radius={[3, 3, 0, 0]}>
                      {wBaseData.map((entry) => <Cell key={entry.model} fill={entry.color} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <p className="mt-2 text-[11px] text-slate-500">
              Removed models receive weight 0. Remaining models' weights are renormalized to sum to 1.
            </p>
          </Card>
        </>
      )}

      {/* Pre-built scenario examples */}
      <Card title="Example scenarios to try" className="mt-4">
        <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["Forecast resilience: NWP outage", "Remove NWP → observe weight redistribution to AI + ensemble."],
            ["AI dominance: +50% boost", "Set AI boost to 0.5 → see shifted forecast and higher uncertainty if disagreement rises."],
            ["Strategy comparison", "Try SKILL_WEIGHTED vs BAYESIAN_AVERAGE → different weight distributions."],
            ["Transition regime stress", "In TRANSITION regime, removing ensemble amplifies uncertainty."],
            ["All models present", "Reset all → baseline is full CONTEXTUAL_ML trust-engine blend."],
            ["Dual removal", "Remove NWP + ensemble → AI-only fallback; significant uncertainty increase expected."],
          ].map(([title, desc]) => (
            <div key={title as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium text-cyan-300 mb-1">{title as string}</div>
              <div className="text-slate-400 text-xs">{desc as string}</div>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
