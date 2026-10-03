"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
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

const VARS = ["RAINFALL", "TEMPERATURE", "WIND_SPEED"];
const LEADS = [6, 12, 24, 48, 72, 120];
const UNITS: Record<string, string> = { RAINFALL: "mm", TEMPERATURE: "°C", WIND_SPEED: "m s⁻¹" };

const MODEL_COLORS: Record<string, string> = {
  "nwp-mock-gfs-like": "#22d3ee",
  "ai-mock-emulator": "#34d399",
  "ens-mock-mean": "#a78bfa",
  "aeris-blend": "#f59e0b",
};
const MODEL_LABELS: Record<string, string> = {
  "nwp-mock-gfs-like": "NWP",
  "ai-mock-emulator": "AI",
  "ens-mock-mean": "Ensemble",
  "aeris-blend": "AERIS",
};

type ForecastDetail = {
  forecast_id: string;
  location: { id: string; name: string; lat: number; lon: number; region: string };
  variable: string;
  lead_time_hours: number;
  valid_time: string;
  value: number;
  units: string;
  dominant_model: string;
  members: Record<string, number>;
  weights: Record<string, number>;
  regime: string;
  uncertainty: {
    spread: number;
    interval: [number, number];
    confidence: string;
    uncertainty_score: number;
    disagreement: number;
    disagreement_label: string;
    frs: number;
    frs_label: string;
    failure_risk: string;
    failure_explanation: string;
  } | null;
  explanation: {
    summary: string;
    reasons: Record<string, string[]>;
    attribution: Record<string, Record<string, number>>;
  } | null;
};

type TimeSeries = {
  series: Record<string, Array<{ t: string; v: number }>>;
};

type SkillByLead = {
  models: Record<string, Array<{ lead: number; mae: number; rmse: number }>>;
};

export default function ForecastExplorer() {
  const [variable, setVariable] = useState("RAINFALL");
  const [lead, setLead] = useState(48);
  const [loc, setLoc] = useState("IN-DL-DEL");
  const [activeTab, setActiveTab] = useState<"detail" | "timeseries" | "skill">("detail");

  const locs = useQuery({
    queryKey: ["locs"],
    queryFn: () => apiGet<{ items: Array<{ id: string; name: string; region: string }> }>("/api/v1/locations"),
  });

  const f = useQuery({
    queryKey: ["fx", loc, variable, lead],
    queryFn: () =>
      apiGet<ForecastDetail>(
        `/api/v1/forecast?location_id=${loc}&variable=${variable}&lead_time_hours=${lead}`,
      ),
    retry: false,
  });

  const ts = useQuery({
    queryKey: ["ts", loc, variable],
    queryFn: () => apiGet<TimeSeries>(`/api/v1/timeseries?location_id=${loc}&variable=${variable}`),
    enabled: activeTab === "timeseries",
    retry: false,
  });

  const skill = useQuery({
    queryKey: ["skill-lead", variable],
    queryFn: () => apiGet<SkillByLead>(`/api/v1/forecast/skill-lead?variable=${variable}`),
    enabled: activeTab === "skill",
    retry: false,
  });

  const u = f.data?.uncertainty;
  const exp = f.data?.explanation;
  const members = f.data?.members ?? {};
  const weights = f.data?.weights ?? {};

  // Bar chart: member forecasts
  const memberChart = useMemo(
    () =>
      Object.entries(members).map(([m, v]) => ({
        model: MODEL_LABELS[m] ?? m,
        value: parseFloat(v?.toFixed?.(2) ?? "0"),
        weight: parseFloat(((weights[m] ?? 0) * 100).toFixed(1)),
        color: MODEL_COLORS[m] ?? "#94a3b8",
      })),
    [members, weights],
  );
  // add AERIS blend
  const memberChartWithBlend = useMemo(
    () =>
      f.data?.value != null
        ? [
            ...memberChart,
            {
              model: "AERIS",
              value: parseFloat(f.data.value.toFixed(2)),
              weight: 100,
              color: "#f59e0b",
            },
          ]
        : memberChart,
    [memberChart, f.data],
  );

  // Time-series chart
  const tsChart = useMemo(() => {
    if (!ts.data?.series) return [];
    const obs = ts.data.series["observation"] ?? [];
    const timeMap: Record<string, Record<string, number | null>> = {};
    obs.forEach(({ t, v }) => {
      timeMap[t] = { observation: v };
    });
    const modelKeys = Object.keys(ts.data.series).filter((k) => k !== "observation");
    modelKeys.forEach((mk) => {
      (ts.data!.series[mk] ?? []).forEach(({ t, v }) => {
        if (!timeMap[t]) timeMap[t] = {};
        timeMap[t][MODEL_LABELS[mk] ?? mk] = v;
      });
    });
    return Object.entries(timeMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([t, vals]) => ({ t: t.slice(5, 16), ...vals }));
  }, [ts.data]);

  // Skill-by-lead chart
  const skillChart = useMemo(() => {
    if (!skill.data?.models) return [];
    const leads = LEADS;
    return leads.map((l) => {
      const pt: Record<string, number | string> = { lead: `${l}h` };
      Object.entries(skill.data!.models).forEach(([m, pts]) => {
        const match = pts.find((p) => p.lead === l);
        if (match) pt[MODEL_LABELS[m] ?? m] = parseFloat(match.mae.toFixed(3));
      });
      return pt;
    });
  }, [skill.data]);

  const frsColor = (frs?: number) =>
    frs == null ? "#94a3b8" : frs >= 80 ? "#34d399" : frs >= 60 ? "#fbbf24" : "#f87171";
  const riskColor = (r?: string) =>
    r === "HIGH" ? "#f87171" : r === "MODERATE" ? "#fbbf24" : "#34d399";

  const cities = (locs.data?.items ?? []).filter((x) => x.id.startsWith("IN-"));

  return (
    <Shell>
      <h1 className="mb-4 text-2xl font-semibold text-white">Forecast Explorer</h1>

      {/* Controls */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Variable</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={variable}
            onChange={(e) => setVariable(e.target.value)}
          >
            {VARS.map((v) => <option key={v}>{v}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Lead time</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={lead}
            onChange={(e) => setLead(Number(e.target.value))}
          >
            {LEADS.map((v) => <option key={v} value={v}>{v}h</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Location</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={loc}
            onChange={(e) => setLoc(e.target.value)}
          >
            {cities.map((x) => (
              <option key={x.id} value={x.id}>{x.name} ({x.region})</option>
            ))}
          </select>
        </div>
        {/* Tab selector */}
        <div className="ml-auto flex items-end gap-1">
          {(["detail", "timeseries", "skill"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`rounded px-3 py-1.5 text-sm capitalize transition-colors ${
                activeTab === t
                  ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              {t === "detail" ? "Forecast detail" : t === "timeseries" ? "Time series" : "Skill vs lead"}
            </button>
          ))}
        </div>
      </div>

      {f.isError && (
        <div className="mb-4 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          No forecast data yet — seed demo data from the Overview page.
        </div>
      )}

      {/* DETAIL TAB */}
      {activeTab === "detail" && (
        <>
          <div className="grid gap-4 lg:grid-cols-3 mb-4">
            {/* AERIS blended value */}
            <Card title="AERIS blended value">
              {f.data ? (
                <>
                  <div className="text-4xl font-semibold text-white">
                    {f.data.value.toFixed(1)}{" "}
                    <span className="text-lg text-slate-400">{UNITS[variable]}</span>
                  </div>
                  <div className="mt-2 text-sm">
                    <span className="text-slate-400">Dominant model: </span>
                    <span style={{ color: MODEL_COLORS[f.data.dominant_model] ?? "#22d3ee" }}>
                      {MODEL_LABELS[f.data.dominant_model] ?? f.data.dominant_model}
                    </span>
                  </div>
                  <div className="mt-1 text-sm">
                    <span className="text-slate-400">Regime: </span>
                    <span className="text-cyan-300">{f.data.regime}</span>
                    <span className="text-[11px] text-slate-500 ml-1">(operational class)</span>
                  </div>
                  <div className="mt-1 text-sm">
                    <span className="text-slate-400">Valid: </span>
                    <span className="text-slate-300">{f.data.valid_time?.slice(0, 16)}Z</span>
                  </div>
                  <div className="mt-1 text-sm">
                    <span className="text-slate-400">Lead: </span>
                    <span className="text-slate-300">{f.data.lead_time_hours}h</span>
                  </div>
                </>
              ) : (
                <div className="text-slate-500 text-sm">Loading…</div>
              )}
            </Card>

            {/* FRS & Uncertainty */}
            <Card title="Reliability & uncertainty">
              {u ? (
                <div className="space-y-2">
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm text-slate-400">FRS</span>
                    <span className="text-2xl font-semibold" style={{ color: frsColor(u.frs) }}>
                      {u.frs}
                    </span>
                  </div>
                  <div className="text-sm" style={{ color: frsColor(u.frs) }}>{u.frs_label}</div>
                  <div className="h-px bg-white/5" />
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Confidence</span>
                    <span className="text-white">{u.confidence}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Uncertainty score</span>
                    <span className="text-white">{u.uncertainty_score}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Disagreement</span>
                    <span className="text-white">{u.disagreement_label} ({u.disagreement})</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">80% interval</span>
                    <span className="text-white font-mono text-xs">
                      [{u.interval[0].toFixed(1)}, {u.interval[1].toFixed(1)}]
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-400">Failure risk</span>
                    <span style={{ color: riskColor(u.failure_risk) }} className="font-medium">
                      {u.failure_risk}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 pt-1">{u.failure_explanation}</p>
                </div>
              ) : (
                <div className="text-slate-500 text-sm">No uncertainty data.</div>
              )}
            </Card>

            {/* WHY THIS FORECAST? */}
            <Card title="WHY THIS FORECAST?">
              {exp ? (
                <div className="space-y-3">
                  <p className="text-sm text-slate-300 leading-relaxed">{exp.summary}</p>
                  <div className="space-y-2">
                    {Object.entries(weights).map(([m, w]) => (
                      <div key={m}>
                        <div className="flex justify-between text-xs mb-0.5">
                          <span style={{ color: MODEL_COLORS[m] ?? "#94a3b8" }}>
                            {MODEL_LABELS[m] ?? m}
                          </span>
                          <span className="text-white font-medium">{(w * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1.5 rounded bg-navy-700">
                          <div
                            className="h-1.5 rounded"
                            style={{ width: `${w * 100}%`, background: MODEL_COLORS[m] ?? "#22d3ee" }}
                          />
                        </div>
                        <ul className="mt-1 text-[11px] text-slate-500 space-y-0.5">
                          {(exp.reasons[m] ?? []).map((r, i) => <li key={i}>· {r}</li>)}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Select a location with seeded data.</p>
              )}
            </Card>
          </div>

          {/* Member comparison bar chart */}
          <Card title={`Member forecasts vs trust weights — ${variable} at ${lead}h`}>
            {memberChartWithBlend.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={memberChartWithBlend} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="model" stroke="#94a3b8" fontSize={11} />
                    <YAxis yAxisId="left" stroke="#94a3b8" fontSize={11} label={{ value: UNITS[variable], angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }} />
                    <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={11} domain={[0, 100]} unit="%" />
                    <Tooltip
                      contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                      formatter={(v: number, name: string) => [
                        name === "weight" ? `${v}%` : `${v} ${UNITS[variable]}`,
                        name === "weight" ? "Trust weight" : "Forecast value",
                      ]}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar yAxisId="left" dataKey="value" name="Forecast value" radius={[3, 3, 0, 0]}>
                      {memberChartWithBlend.map((entry) => (
                        <Cell key={entry.model} fill={entry.color} />
                      ))}
                    </Bar>
                    <Bar yAxisId="right" dataKey="weight" name="Trust weight %" fill="#475569" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                Seed demo data to see member comparison.
              </div>
            )}
            <p className="mt-2 text-[11px] text-slate-500">
              Weights are always ≥ 0 and sum to 1. AERIS is the trust-weighted blend of all sources.
            </p>
          </Card>
        </>
      )}

      {/* TIME SERIES TAB */}
      {activeTab === "timeseries" && (
        <Card title={`${variable} time series — ${loc} (48h lead)`}>
          {ts.isLoading && <div className="h-72 flex items-center justify-center text-slate-500">Loading…</div>}
          {ts.isError && <div className="text-sm text-amber-300">No time-series data — seed demo data first.</div>}
          {tsChart.length > 0 && (
            <>
              <div className="h-72">
                <ResponsiveContainer>
                  <LineChart data={tsChart} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="t" stroke="#94a3b8" fontSize={10} />
                    <YAxis stroke="#94a3b8" fontSize={11} unit={` ${UNITS[variable]}`} />
                    <Tooltip
                      contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="observation" stroke="#f59e0b" dot={false} name="Observation" strokeWidth={2} />
                    <Line type="monotone" dataKey="NWP" stroke="#22d3ee" dot={false} strokeDasharray="4 2" name="NWP" />
                    <Line type="monotone" dataKey="AI" stroke="#34d399" dot={false} strokeDasharray="4 2" name="AI" />
                    <Line type="monotone" dataKey="Ensemble" stroke="#a78bfa" dot={false} strokeDasharray="4 2" name="Ensemble" />
                    <Line type="monotone" dataKey="AERIS" stroke="#f59e0b" dot={false} strokeWidth={2} name="AERIS blend" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                Demonstration benchmark data. Individual model and AERIS blend vs synthetic observations.
              </p>
            </>
          )}
        </Card>
      )}

      {/* SKILL VS LEAD TAB */}
      {activeTab === "skill" && (
        <Card title={`MAE vs lead time — ${variable} (all models)`}>
          {skill.isLoading && <div className="h-72 flex items-center justify-center text-slate-500">Loading…</div>}
          {skillChart.length > 0 && (
            <>
              <div className="h-72">
                <ResponsiveContainer>
                  <LineChart data={skillChart} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="lead" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="NWP" stroke="#22d3ee" dot={true} strokeWidth={2} />
                    <Line type="monotone" dataKey="AI" stroke="#34d399" dot={true} strokeWidth={2} />
                    <Line type="monotone" dataKey="Ensemble" stroke="#a78bfa" dot={true} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                DEMONSTRATION BENCHMARK — lower MAE = better skill. Controlled error hierarchy: NWP stronger long-lead/MONSOON; AI stronger short-lead/convective.
              </p>
            </>
          )}
        </Card>
      )}
    </Shell>
  );
}
