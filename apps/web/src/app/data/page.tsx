"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Shell, Card } from "@/components/shell";
import { apiGet, apiPost } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "#34d399",
  DEGRADED: "#fbbf24",
  OFFLINE: "#f87171",
};

type DataSource = {
  id: string;
  name: string;
  status: string;
  latest_update: string | null;
  variables: string[];
  resolution: string;
  coverage: string;
  quality: string;
};

export default function DataHub() {
  const [importFormat, setImportFormat] = useState("CSV");
  const [importNote, setImportNote] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["dh"],
    queryFn: () =>
      apiGet<{ items: DataSource[]; import_formats: string[] }>("/api/v1/data-hub"),
  });

  const tryImport = useMutation({
    mutationFn: () =>
      apiPost<{ accepted: boolean; reason: string; format: string }>(
        "/api/v1/data-hub/import",
        { format: importFormat, payload: null },
      ),
    onSuccess: (d) => setImportNote(d.reason),
  });

  const items = q.data?.items ?? [];
  const active = items.filter((s) => s.status === "ACTIVE").length;
  const degraded = items.filter((s) => s.status !== "ACTIVE" && s.status !== "OFFLINE").length;

  return (
    <Shell>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-white">Data hub</h1>
        <p className="mt-0.5 text-sm text-slate-400">
          Forecast source registry, observation feeds, data quality status, and import surface.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="rounded-lg border border-cyan-900/25 bg-navy-800 px-4 py-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Active sources</div>
          <div className="mt-1 text-2xl font-semibold text-green-400">{active}</div>
        </div>
        <div className="rounded-lg border border-cyan-900/25 bg-navy-800 px-4 py-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Degraded / offline</div>
          <div className="mt-1 text-2xl font-semibold text-amber-400">{degraded}</div>
        </div>
        <div className="rounded-lg border border-cyan-900/25 bg-navy-800 px-4 py-3">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Total sources</div>
          <div className="mt-1 text-2xl font-semibold text-white">{items.length}</div>
        </div>
      </div>

      {/* Source cards */}
      <div className="grid gap-3 md:grid-cols-2 mb-5">
        {items.map((s) => (
          <Card key={s.id}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="font-semibold text-white">{s.name}</div>
                <div className="text-xs text-slate-500 mt-0.5 font-mono">{s.id}</div>
              </div>
              <div
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  color: STATUS_COLORS[s.status] ?? "#94a3b8",
                  background: (STATUS_COLORS[s.status] ?? "#94a3b8") + "22",
                }}
              >
                {s.status}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              <div>
                <div className="text-slate-500">Latest update</div>
                <div className="text-slate-300">{s.latest_update?.slice(0, 16) ?? "—"}Z</div>
              </div>
              <div>
                <div className="text-slate-500">Resolution</div>
                <div className="text-slate-300">{s.resolution}</div>
              </div>
              <div>
                <div className="text-slate-500">Coverage</div>
                <div className="text-slate-300">{s.coverage}</div>
              </div>
              <div>
                <div className="text-slate-500">Quality</div>
                <div className="text-slate-300">{s.quality}</div>
              </div>
            </div>
            <div className="mt-2">
              <div className="text-[11px] text-slate-500 mb-1">Variables</div>
              <div className="flex flex-wrap gap-1">
                {(s.variables ?? []).map((v) => (
                  <span key={v} className="rounded bg-navy-700 px-1.5 py-0.5 text-[10px] text-cyan-300">
                    {v}
                  </span>
                ))}
              </div>
            </div>
          </Card>
        ))}
        {items.length === 0 && (
          <div className="col-span-2 text-center py-12 text-slate-500 text-sm">
            Seed demo data from Overview to populate sources.
          </div>
        )}
      </div>

      {/* Adapter architecture */}
      <Card title="Adapter architecture" className="mb-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["MockNWPAdapter", "GFS-like demo", "Deterministic synthetic NWP forecast with controlled error hierarchy", "ACTIVE"],
            ["MockAIAdapter", "AI emulator demo", "Short-lead AI emulator; stronger at convective regimes in benchmark", "ACTIVE"],
            ["MockEnsembleAdapter", "Ensemble demo", "Mean of synthetic ensemble members; robust in transition", "ACTIVE"],
            ["RealNWPAdapter (stub)", "Operational NWP", "Configure NWP_BASE_URL + NWP_API_KEY via .env. No architectural change needed.", "STUB"],
          ].map(([name, type, desc, status]) => (
            <div key={name as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium text-white mb-0.5">{name as string}</div>
              <div
                className="rounded px-1.5 py-0.5 text-[10px] font-medium inline-block mb-2"
                style={{
                  color: status === "ACTIVE" ? "#34d399" : "#fbbf24",
                  background: status === "ACTIVE" ? "#34d39922" : "#fbbf2422",
                }}
              >
                {status as string}
              </div>
              <div className="text-xs text-cyan-400 mb-1">{type as string}</div>
              <div className="text-xs text-slate-400">{desc as string}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-slate-500">
          Future adapters: SatelliteAdapter · RadarAdapter · ObservationAdapter (real) — all implement the same BaseForecastAdapter interface.
          Adding a new model does NOT require changing the blending engine.
        </p>
      </Card>

      {/* Import surface */}
      <Card title="Data import (prototype hook)">
        <p className="text-sm text-slate-400 mb-4">
          Operational ingest requires configured adapters and validated grids. This prototype hook demonstrates the import surface.
        </p>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] uppercase tracking-wider text-slate-500">Format</label>
            <select
              className="rounded border border-cyan-900/40 bg-navy-900 px-3 py-1.5 text-sm text-slate-200"
              value={importFormat}
              onChange={(e) => setImportFormat(e.target.value)}
            >
              {(q.data?.import_formats ?? ["CSV", "JSON", "NetCDF"]).map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => tryImport.mutate()}
            disabled={tryImport.isPending}
            className="rounded border border-cyan-500/40 px-4 py-2 text-sm text-cyan-200 hover:bg-cyan-500/10 transition-colors disabled:opacity-50"
          >
            {tryImport.isPending ? "Trying…" : "Test import hook"}
          </button>
        </div>
        {importNote && (
          <div className="mt-3 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
            {importNote}
          </div>
        )}
        <p className="mt-3 text-[11px] text-slate-500">
          Supported import path: CSV (station observations), JSON (harmonized field), NetCDF (gridded forecast).
          All inputs pass through the harmonization + QC pipeline before entering the blending engine.
        </p>
      </Card>
    </Shell>
  );
}
