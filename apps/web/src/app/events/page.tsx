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
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const IndiaMap = dynamic(() => import("@/components/india-map").then((m) => m.IndiaMap), { ssr: false });

const EVENT_COLORS: Record<string, string> = {
  heavy_rainfall: "#3b82f6",
  heatwave: "#f87171",
  high_wind: "#fbbf24",
};
const EVENT_ICONS: Record<string, string> = {
  heavy_rainfall: "🌧",
  heatwave: "🌡",
  high_wind: "💨",
};
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

type EventItem = {
  event_id: string;
  event_type: string;
  location_id: string;
  location_name: string;
  lat: number;
  lon: number;
  probability: number;
  intensity_range: [number, number];
  confidence: string;
  lead_time_hours: number;
  primary_model: string;
  supporting_models: string[];
  disagreement: number;
  forecast_failure_risk: string;
  start_time: string;
  end_time: string;
};

export default function EventsPage() {
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("");

  const q = useQuery({
    queryKey: ["ex"],
    queryFn: () =>
      apiGet<{ thresholds_note: string; items: EventItem[] }>("/api/v1/extremes"),
  });

  const items = q.data?.items ?? [];
  const filtered = filterType ? items.filter((e) => e.event_type === filterType) : items;

  const groups = ["heavy_rainfall", "heatwave", "high_wind"];
  const groupSummary = groups.map((g) => {
    const evs = items.filter((e) => e.event_type === g);
    const top = evs.sort((a, b) => b.probability - a.probability)[0];
    return { type: g, count: evs.length, top };
  });

  // Map points
  const mapPoints = filtered.map((e) => ({
    id: e.event_id,
    lat: e.lat,
    lon: e.lon,
    label: e.location_name,
    extra: `${e.event_type.replace("_", " ")} · p=${(e.probability * 100).toFixed(0)}% · ${e.forecast_failure_risk} risk`,
    color: EVENT_COLORS[e.event_type] ?? "#22d3ee",
  }));

  // Bar chart: probability by location (top 15)
  const probChart = [...filtered]
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 15)
    .map((e) => ({
      name: e.location_name.slice(0, 12),
      probability: parseFloat((e.probability * 100).toFixed(1)),
      type: e.event_type,
    }));

  const selectedItem = items.find((e) => e.event_id === selectedEvent);

  return (
    <Shell>
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-white">Extreme event intelligence</h1>
        <p className="mt-1 text-xs text-slate-500">{q.data?.thresholds_note}</p>
      </div>

      {/* Event type cards */}
      <div className="grid gap-4 md:grid-cols-3 mb-5 mt-4">
        {groupSummary.map(({ type, count, top }) => (
          <button
            key={type}
            onClick={() => setFilterType(filterType === type ? "" : type)}
            className={`text-left rounded-lg border p-4 transition-all ${
              filterType === type
                ? "border-opacity-80 bg-opacity-20"
                : "border-white/10 bg-navy-800 hover:border-white/20"
            }`}
            style={
              filterType === type
                ? {
                    borderColor: EVENT_COLORS[type],
                    background: EVENT_COLORS[type] + "18",
                  }
                : {}
            }
          >
            <div className="flex items-center justify-between mb-2">
              <div className="text-xl">{EVENT_ICONS[type]}</div>
              <div className="text-xs text-slate-500">{count} locations</div>
            </div>
            <div className="text-lg font-semibold" style={{ color: EVENT_COLORS[type] }}>
              {top ? `${(top.probability * 100).toFixed(0)}%` : "—"}
            </div>
            <div className="text-sm font-medium text-white mt-0.5 capitalize">
              {type.replace("_", " ")}
            </div>
            {top && (
              <>
                <div className="text-xs text-slate-400 mt-1">{top.location_name}</div>
                <div className="flex gap-2 mt-2">
                  <span
                    className="rounded px-1.5 py-0.5 text-[10px] font-medium"
                    style={{ color: CONF_COLORS[top.confidence], background: (CONF_COLORS[top.confidence]) + "22" }}
                  >
                    {top.confidence}
                  </span>
                  <span
                    className="rounded px-1.5 py-0.5 text-[10px] font-medium"
                    style={{ color: RISK_COLORS[top.forecast_failure_risk], background: (RISK_COLORS[top.forecast_failure_risk]) + "22" }}
                  >
                    {top.forecast_failure_risk} risk
                  </span>
                </div>
              </>
            )}
            {!top && <div className="text-xs text-slate-500 mt-1">No events above threshold</div>}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3 mb-4">
        {/* Map */}
        <Card title="Event locations map" className="lg:col-span-2">
          <div className="mb-2 flex flex-wrap gap-2 text-[11px]">
            {groups.map((g) => (
              <div key={g} className="flex items-center gap-1.5 text-slate-400">
                <div className="h-2 w-2 rounded-full" style={{ background: EVENT_COLORS[g] }} />
                {g.replace("_", " ")}
              </div>
            ))}
            <span className="text-slate-500 ml-2">Click a point for details</span>
          </div>
          <IndiaMap
            points={mapPoints}
            onSelect={(id: string) => {
              const ev = items.find((e) => e.event_id === id);
              if (ev) setSelectedEvent(id);
            }}
          />
        </Card>

        {/* Selected event detail */}
        <Card title="Event detail">
          {selectedItem ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-xl">{EVENT_ICONS[selectedItem.event_type]}</span>
                <div>
                  <div className="font-semibold text-white capitalize">{selectedItem.event_type.replace("_", " ")}</div>
                  <div className="text-xs text-slate-400">{selectedItem.location_name}</div>
                </div>
              </div>
              <div className="rounded bg-navy-700/60 px-3 py-2 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Probability</span>
                  <span className="text-white font-semibold text-lg">{(selectedItem.probability * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Intensity range</span>
                  <span className="font-mono text-white">
                    [{selectedItem.intensity_range[0].toFixed(1)}, {selectedItem.intensity_range[1].toFixed(1)}]
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Lead time</span>
                  <span className="text-white">{selectedItem.lead_time_hours}h</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Confidence</span>
                  <span style={{ color: CONF_COLORS[selectedItem.confidence] }}>{selectedItem.confidence}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Failure risk</span>
                  <span style={{ color: RISK_COLORS[selectedItem.forecast_failure_risk] }}>{selectedItem.forecast_failure_risk}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Disagreement</span>
                  <span className="text-white">{selectedItem.disagreement?.toFixed?.(3)}</span>
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500 mb-1">Contributing models</div>
                <div className="text-xs text-slate-300">
                  <span className="text-cyan-300">Primary:</span> {selectedItem.primary_model?.split("-")[0]}
                </div>
                <div className="text-xs text-slate-300 mt-0.5">
                  <span className="text-slate-400">Supporting:</span>{" "}
                  {selectedItem.supporting_models?.map((m) => m.split("-")[0]).join(", ") || "none"}
                </div>
              </div>
              <div className="text-[11px] text-slate-500">
                Valid: {selectedItem.start_time?.slice(0, 16)}Z → {selectedItem.end_time?.slice(0, 16)}Z
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Click a map point or table row to see event details.
            </p>
          )}
        </Card>
      </div>

      {/* Probability bar chart */}
      {probChart.length > 0 && (
        <Card title="Event probability by location (top 15)">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={probChart} layout="vertical" margin={{ top: 4, right: 32, left: 88, bottom: 0 }}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={11} domain={[0, 100]} unit="%" />
                <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={86} />
                <Tooltip
                  contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }}
                  formatter={(v: number) => [`${v}%`, "Probability"]}
                />
                <Bar dataKey="probability" radius={[0, 3, 3, 0]}>
                  {probChart.map((entry) => (
                    <Cell key={entry.name} fill={EVENT_COLORS[entry.type] ?? "#22d3ee"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Events table */}
      <Card title="All flagged events" className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-white/10">
                <th className="pb-2 pr-3">Type</th>
                <th className="pb-2 pr-3">Location</th>
                <th className="pb-2 pr-3">Probability</th>
                <th className="pb-2 pr-3">Confidence</th>
                <th className="pb-2 pr-3">Lead</th>
                <th className="pb-2 pr-3">Primary model</th>
                <th className="pb-2">Failure risk</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 40).map((e) => (
                <tr
                  key={e.event_id}
                  className={`border-t border-white/5 cursor-pointer hover:bg-white/2 ${selectedEvent === e.event_id ? "bg-white/4" : ""}`}
                  onClick={() => setSelectedEvent(e.event_id)}
                >
                  <td className="py-1.5 pr-3 capitalize" style={{ color: EVENT_COLORS[e.event_type] ?? "#94a3b8" }}>
                    {EVENT_ICONS[e.event_type]} {e.event_type.replace("_", " ")}
                  </td>
                  <td className="py-1.5 pr-3 text-slate-300">{e.location_name}</td>
                  <td className="py-1.5 pr-3 font-mono text-white">{(e.probability * 100).toFixed(0)}%</td>
                  <td className="py-1.5 pr-3" style={{ color: CONF_COLORS[e.confidence] }}>{e.confidence}</td>
                  <td className="py-1.5 pr-3 text-slate-400">{e.lead_time_hours}h</td>
                  <td className="py-1.5 pr-3 text-slate-400">{e.primary_model?.split("-")[0]}</td>
                  <td className="py-1.5" style={{ color: RISK_COLORS[e.forecast_failure_risk] }}>{e.forecast_failure_risk}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          Prototype thresholds: rainfall ≥ 50 mm · temperature ≥ 40°C · wind ≥ 12 m s⁻¹. Configurable — not official IMD/NCMRWF warning thresholds.
        </p>
      </Card>
    </Shell>
  );
}
