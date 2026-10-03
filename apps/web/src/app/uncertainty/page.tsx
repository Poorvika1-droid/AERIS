"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Shell, Card } from "@/components/shell";
import { apiGet } from "@/lib/api";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  ErrorBar,
  Legend,
  Line,
  RadialBar,
  RadialBarChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
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
  { id: "IN-KL-KOY", name: "Kochi" },
  { id: "IN-RJ-JAI", name: "Jaipur" },
];

const RISK_COLORS: Record<string, string> = {
  HIGH: "#f87171",
  MODERATE: "#fbbf24",
  LOW: "#34d399",
};
const CONF_COLORS: Record<string, string> = {
  HIGH: "#34d399",
  MODERATE: "#fbbf24",
  LOW: "#f87171",
};
const FRS_COLOR = (frs: number) =>
  frs >= 80 ? "#34d399" : frs >= 60 ? "#fbbf24" : "#f87171";

type ForecastDetail = {
  forecast_id: string;
  value: number;
  units: string;
  dominant_model: string;
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
    frs_components: Record<string, number>;
    failure_risk: string;
    failure_explanation: string;
  } | null;
};

type UncertSeries = {
  points: Array<{
    lead: number;
    value: number;
    low: number;
    high: number;
    spread: number;
    frs: number;
    disagreement: number;
    confidence: string;
    failure_risk: string;
  }>;
};

export default function UncertaintyPage() {
  const [loc, setLoc] = useState("IN-DL-DEL");
  const [variable, setVariable] = useState("RAINFALL");

  const f = useQuery({
    queryKey: ["u", loc, variable],
    queryFn: () =>
      apiGet<ForecastDetail>(
        `/api/v1/forecast?location_id=${loc}&variable=${variable}&lead_time_hours=48`,
      ),
    retry: false,
  });

  const series = useQuery({
    queryKey: ["uset", loc, variable],
    queryFn: () =>
      apiGet<UncertSeries>(
        `/api/v1/forecast/uncertainty-series?location_id=${loc}&variable=${variable}`,
      ),
    retry: false,
  });

  const u = f.data?.uncertainty;
  const comp = u?.frs_components ?? {};
  const pts = series.data?.points ?? [];

  // FRS radial gauge data
  const gaugeData = u ? [{ name: "FRS", value: u.frs, fill: FRS_COLOR(u.frs) }] : [];

  // FRS components bar
  const compData = Object.entries(comp).map(([k, v]) => ({
    name: k.replace(/_/g, " "),
    value: parseFloat(typeof v === "number" ? v.toFixed(1) : "0"),
  }));

  // Uncertainty interval chart
  const intervalData = pts.map((p) => ({
    lead: `${p.lead}h`,
    value: p.value,
    low: p.low,
    high: p.high,
    spread: p.spread,
    frs: p.frs,
    disagreement: parseFloat((p.disagreement * 100).toFixed(1)),
  }));

  return (
    <Shell>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-white">Uncertainty & Reliability</h1>
        <p className="mt-1 text-sm text-slate-400">
          Forecast uncertainty is information, not a failure.{" "}
          <strong className="text-white">Uncertainty ≠ confidence ≠ FRS.</strong> Each is a distinct concept.
        </p>
      </div>

      {/* Controls */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-[11px] uppercase tracking-wider text-slate-500">Location</label>
          <select
            className="rounded border border-cyan-900/40 bg-navy-800 px-3 py-1.5 text-sm text-slate-200"
            value={loc}
            onChange={(e) => setLoc(e.target.value)}
          >
            {CITY_OPTIONS.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
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
      </div>

      {f.isError && (
        <div className="mb-4 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          No data — seed demo data from Overview first.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-4 mb-4">
        {/* FRS gauge */}
        <Card title="Forecast reliability score">
          {u ? (
            <>
              <div className="h-32">
                <ResponsiveContainer>
                  <RadialBarChart
                    cx="50%"
                    cy="100%"
                    innerRadius="55%"
                    outerRadius="90%"
                    startAngle={180}
                    endAngle={0}
                    data={gaugeData}
                  >
                    <RadialBar dataKey="value" background={{ fill: "#1a2740" }} cornerRadius={4} />
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
              <div className="text-center -mt-8">
                <div className="text-4xl font-semibold" style={{ color: FRS_COLOR(u.frs) }}>{u.frs}</div>
                <div className="text-sm mt-1" style={{ color: FRS_COLOR(u.frs) }}>{u.frs_label}</div>
              </div>
              <p className="mt-2 text-[11px] text-slate-500 text-center">
                Decision-support summary 0–100. Not a universal scientific metric.
              </p>
            </>
          ) : (
            <div className="h-32 flex items-center justify-center text-slate-500 text-sm">—</div>
          )}
        </Card>

        {/* Forecast value + interval */}
        <Card title="Forecast value & 80% interval">
          {f.data && u ? (
            <div className="space-y-3">
              <div>
                <div className="text-4xl font-semibold text-white">
                  {f.data.value.toFixed(1)}
                </div>
                <div className="text-sm text-slate-400">{f.data.units} · 48h lead</div>
              </div>
              <div className="rounded bg-navy-700/60 px-3 py-2 text-sm">
                <div className="flex justify-between text-slate-300">
                  <span>80% interval</span>
                  <span className="font-mono">[{u.interval[0].toFixed(1)}, {u.interval[1].toFixed(1)}]</span>
                </div>
                <div className="flex justify-between mt-1 text-slate-400">
                  <span>Spread (σ)</span>
                  <span className="font-mono">{u.spread.toFixed(3)}</span>
                </div>
                <div className="flex justify-between mt-1 text-slate-400">
                  <span>Uncertainty score</span>
                  <span className="font-mono">{u.uncertainty_score}</span>
                </div>
              </div>
              <div className="rounded bg-navy-700/60 px-3 py-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Confidence</span>
                  <span style={{ color: CONF_COLORS[u.confidence] ?? "#94a3b8" }} className="font-medium">{u.confidence}</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-slate-400">Disagreement</span>
                  <span className="text-white">{u.disagreement_label}</span>
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-slate-400">Failure risk</span>
                  <span style={{ color: RISK_COLORS[u.failure_risk] ?? "#94a3b8" }} className="font-medium">{u.failure_risk}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-sm">—</div>
          )}
        </Card>

        {/* Failure risk explanation */}
        <Card title="Forecast failure risk" className="lg:col-span-2">
          {u ? (
            <div className="space-y-3">
              <div
                className="rounded px-4 py-3 text-center text-2xl font-bold"
                style={{
                  color: RISK_COLORS[u.failure_risk] ?? "#94a3b8",
                  background: (RISK_COLORS[u.failure_risk] ?? "#94a3b8") + "22",
                  border: `1px solid ${(RISK_COLORS[u.failure_risk] ?? "#94a3b8")}44`,
                }}
              >
                {u.failure_risk}
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{u.failure_explanation}</p>
              <div className="grid grid-cols-3 gap-2 text-xs">
                {[
                  ["Disagreement", `${(u.disagreement * 100).toFixed(0)}%`, "score"],
                  ["Uncertainty", u.uncertainty_score, "score"],
                  ["Regime FRS", comp["regime_certainty"]?.toFixed(1) ?? "—", "certainty"],
                ].map(([label, value, unit]) => (
                  <div key={label as string} className="rounded border border-white/5 bg-navy-900/60 px-2 py-2 text-center">
                    <div className="text-slate-400">{label as string}</div>
                    <div className="text-white font-mono mt-0.5">{String(value)}</div>
                    <div className="text-slate-500">{unit as string}</div>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-slate-500">
                Decision-support indicator only. Not a claim of certain forecast failure.
              </p>
            </div>
          ) : (
            <div className="text-slate-500 text-sm">No data yet.</div>
          )}
        </Card>
      </div>

      {/* FRS components */}
      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        <Card title="FRS components breakdown (weighted contribution to 0–100 score)">
          {compData.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <BarChart data={compData} layout="vertical" margin={{ top: 4, right: 32, left: 120, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" stroke="#94a3b8" fontSize={11} domain={[0, 100]} />
                  <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={118} />
                  <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                    {compData.map((entry, i) => (
                      <Cell key={i} fill={entry.value >= 75 ? "#34d399" : entry.value >= 50 ? "#fbbf24" : "#f87171"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            Components: historical skill (0.25) · model health (0.15) · inter-model agreement (0.20) · regime certainty (0.15) · observation consistency (0.15) · forecast stability (0.10).
          </p>
        </Card>

        {/* Uncertainty series across leads */}
        <Card title="Uncertainty interval across lead times">
          {intervalData.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <ComposedChart data={intervalData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="lead" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="high" stroke="transparent" fill="#22d3ee" fillOpacity={0.15} name="Upper bound" />
                  <Area type="monotone" dataKey="low" stroke="transparent" fill="#070b14" fillOpacity={1} name="Lower bound" />
                  <Line type="monotone" dataKey="value" stroke="#22d3ee" strokeWidth={2} dot={true} name="Blended forecast" />
                  <Line type="monotone" dataKey="frs" stroke="#fbbf24" strokeDasharray="4 2" name="FRS" yAxisId="frs" />
                  <YAxis yAxisId="frs" orientation="right" stroke="#64748b" fontSize={11} domain={[0, 100]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            Shaded area = 80%-ish prediction interval. Uncertainty grows with lead time. FRS (right axis) captures combined reliability.
          </p>
        </Card>
      </div>

      {/* Conceptual clarification */}
      <Card title="Conceptual distinctions">
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          {[
            [
              "Forecast uncertainty",
              "How spread out are the member forecasts? Measured by ensemble/inter-model spread. Always present — it is information.",
              "#22d3ee",
            ],
            [
              "Forecast confidence",
              "Composite of spread + disagreement. HIGH = narrow spread + low disagreement. Not the same as low uncertainty score.",
              "#34d399",
            ],
            [
              "Forecast reliability score (FRS)",
              "Multi-component decision-support summary (0–100) built from historical skill, health, agreement, regime certainty, etc. Not a universal scientific metric.",
              "#fbbf24",
            ],
          ].map(([title, desc, color]) => (
            <div key={title as string} className="rounded border border-white/5 bg-navy-900/60 px-4 py-3">
              <div className="font-semibold mb-2" style={{ color: color as string }}>{title as string}</div>
              <p className="text-slate-400 text-xs leading-relaxed">{desc as string}</p>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
