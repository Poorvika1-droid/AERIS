"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Shell, Card } from "@/components/shell";
import { apiGet, apiPost } from "@/lib/api";
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

const STAGE_COLORS: Record<string, string> = {
  Production: "#34d399",
  Staging: "#fbbf24",
  Archived: "#6b7280",
  "demonstration-benchmark": "#22d3ee",
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "#34d399",
  DEGRADED: "#fbbf24",
  OFFLINE: "#f87171",
  HEALTHY: "#34d399",
};

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
  "aeris-blend": "AERIS blend",
};

type MLModel = {
  id: string;
  name: string;
  version: string;
  stage: string;
  strategy: string;
  metrics: Record<string, unknown>;
  hyperparameters: Record<string, unknown>;
  dataset_version: string;
  feature_version: string;
  mlflow_run_id: string | null;
  trained_at: string;
  validation_status: string;
};

type ForecastSource = {
  model_id: string;
  model_name: string;
  provider: string;
  model_type: string;
  status: string;
  resolution: string;
  coverage: string;
  variables: string[];
};

type SkillHeatmap = {
  models: string[];
  leads: number[];
  grid: Record<string, Record<number, number>>;
};

export default function RegistryPage() {
  const ml = useQuery({
    queryKey: ["ml"],
    queryFn: () => apiGet<{ items: MLModel[] }>("/api/v1/ml/registry"),
  });
  const models = useQuery({
    queryKey: ["models"],
    queryFn: () => apiGet<{ items: ForecastSource[] }>("/api/v1/models"),
  });
  const hmap = useQuery({
    queryKey: ["hmap-rain"],
    queryFn: () => apiGet<SkillHeatmap>("/api/v1/skill/heatmap?variable=RAINFALL"),
  });
  const learn = useMutation({ mutationFn: () => apiPost("/api/v1/admin/learn") });

  // Build skill table from heatmap
  const hmapData =
    hmap.data
      ? hmap.data.models.map((m) => {
          const row: Record<string, string | number> = {
            model: MODEL_LABELS[m] ?? m,
            color: MODEL_COLORS[m] ?? "#94a3b8",
          };
          hmap.data!.leads.forEach((l) => {
            row[`${l}h`] = parseFloat((hmap.data!.grid[m]?.[l] ?? 0).toFixed(3));
          });
          return row;
        })
      : [];

  // For bar chart: average MAE per model
  const avgMaeData =
    hmap.data
      ? hmap.data.models.map((m) => {
          const vals = Object.values(hmap.data!.grid[m] ?? {}).filter((v): v is number => typeof v === "number");
          const avg = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
          return { model: MODEL_LABELS[m] ?? m, "Avg MAE": parseFloat(avg.toFixed(3)), color: MODEL_COLORS[m] ?? "#94a3b8" };
        })
      : [];

  return (
    <Shell>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-white">Model registry / plug-in center</h1>
        <p className="mt-0.5 text-sm text-slate-400">
          New forecast models are evaluated against historical benchmark data before production blending.
          Meta-model versions tracked via MLflow. Demo sources are pre-registered.
        </p>
      </div>

      {/* Trust meta-models */}
      <Card title="Trust meta-model registry" className="mb-4">
        {(ml.data?.items ?? []).length > 0 ? (
          <div className="space-y-3">
            {(ml.data?.items ?? []).map((m) => (
              <div key={m.id} className="rounded border border-white/5 bg-navy-900/60 px-4 py-3">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-semibold text-white">{m.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5 font-mono">id: {m.id} · v{m.version}</div>
                  </div>
                  <div className="flex gap-2">
                    <span
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        color: STAGE_COLORS[m.stage] ?? "#94a3b8",
                        background: (STAGE_COLORS[m.stage] ?? "#94a3b8") + "22",
                      }}
                    >
                      {m.stage}
                    </span>
                    <span
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        color: STAGE_COLORS[m.validation_status] ?? "#22d3ee",
                        background: (STAGE_COLORS[m.validation_status] ?? "#22d3ee") + "22",
                      }}
                    >
                      {m.validation_status}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
                  <div>
                    <div className="text-slate-500">Strategy</div>
                    <div className="text-cyan-300">{m.strategy}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Dataset</div>
                    <div className="text-slate-300">{m.dataset_version}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Features</div>
                    <div className="text-slate-300">{m.feature_version}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Trained</div>
                    <div className="text-slate-300">{m.trained_at?.slice(0, 16)}Z</div>
                  </div>
                </div>
                <div className="mt-2 text-xs">
                  <span className="text-slate-500">MLflow run: </span>
                  <span className="font-mono text-slate-400">
                    {m.mlflow_run_id ?? "not logged (MLflow server optional in prototype)"}
                  </span>
                </div>
                {Object.keys(m.metrics).length > 0 && (
                  <div className="mt-2 text-xs">
                    <span className="text-slate-500">Metrics: </span>
                    <span className="text-slate-400">{JSON.stringify(m.metrics)}</span>
                  </div>
                )}
                {Object.keys(m.hyperparameters).length > 0 && (
                  <div className="mt-1 text-xs">
                    <span className="text-slate-500">Hyperparameters: </span>
                    <span className="text-slate-400">{JSON.stringify(m.hyperparameters)}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Seed demo data to populate.</p>
        )}
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={() => learn.mutate()}
            disabled={learn.isPending}
            className="rounded bg-cyan-500 px-4 py-2 text-sm font-semibold text-navy-950 hover:bg-cyan-400 transition-colors disabled:opacity-50"
          >
            {learn.isPending ? "Recalibrating…" : "Run continuous learning step"}
          </button>
          <span className="text-xs text-slate-500">Updates skill memory, health, blend weights, and verification.</span>
        </div>
        {learn.isSuccess && (
          <div className="mt-2 text-sm text-green-300">
            Done — elapsed {(learn.data as { elapsed_s?: number })?.elapsed_s ?? "—"}s
          </div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2 mb-4">
        {/* Average MAE per model */}
        <Card title="Average MAE across lead times (rainfall)">
          {avgMaeData.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer>
                <BarChart data={avgMaeData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="model" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#111b2e", border: "1px solid #1e3a4c", fontSize: 11 }} />
                  <Bar dataKey="Avg MAE" radius={[3, 3, 0, 0]}>
                    {avgMaeData.map((e) => <Cell key={e.model} fill={e.color as string} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">DEMONSTRATION BENCHMARK — lower = better.</p>
        </Card>

        {/* Skill heatmap table */}
        <Card title="Skill heatmap — MAE by model × lead time">
          {hmapData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="text-slate-500 border-b border-white/10">
                    <th className="pb-2 pr-3">Model</th>
                    {hmap.data!.leads.map((l) => (
                      <th key={l} className="pb-2 pr-2 text-right">{l}h</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {hmapData.map((row) => (
                    <tr key={row.model as string} className="border-t border-white/5">
                      <td className="py-1.5 pr-3 font-medium" style={{ color: row.color as string }}>
                        {row.model as string}
                      </td>
                      {hmap.data!.leads.map((l) => {
                        const v = row[`${l}h`] as number;
                        const heat = v < 1.5 ? "#34d399" : v < 3 ? "#fbbf24" : "#f87171";
                        return (
                          <td key={l} className="py-1.5 pr-2 text-right font-mono" style={{ color: heat }}>
                            {v?.toFixed?.(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-500 text-sm">No data.</div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            Green = low error · Yellow = moderate · Red = high. DEMONSTRATION BENCHMARK.
          </p>
        </Card>
      </div>

      {/* Forecast sources */}
      <Card title="Registered forecast sources">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-white/10">
                <th className="pb-2 pr-3">Model</th>
                <th className="pb-2 pr-3">Provider</th>
                <th className="pb-2 pr-3">Type</th>
                <th className="pb-2 pr-3">Status</th>
                <th className="pb-2 pr-3">Resolution</th>
                <th className="pb-2">Variables</th>
              </tr>
            </thead>
            <tbody>
              {(models.data?.items ?? []).map((m) => (
                <tr key={m.model_id} className="border-t border-white/5">
                  <td className="py-2 pr-3 font-medium" style={{ color: MODEL_COLORS[m.model_id] ?? "#94a3b8" }}>
                    {m.model_name}
                  </td>
                  <td className="py-2 pr-3 text-slate-400">{m.provider}</td>
                  <td className="py-2 pr-3 text-slate-400">{m.model_type}</td>
                  <td className="py-2 pr-3">
                    <span
                      className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
                      style={{
                        color: STATUS_COLORS[m.status] ?? "#94a3b8",
                        background: (STATUS_COLORS[m.status] ?? "#94a3b8") + "22",
                      }}
                    >
                      {m.status}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-slate-400">{m.resolution}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {(m.variables ?? []).map((v) => (
                        <span key={v} className="rounded bg-navy-700 px-1 py-0.5 text-[10px] text-cyan-300">{v}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* MLOps pipeline description */}
      <Card title="MLflow integration & model lifecycle" className="mt-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Experiment tracking", "Each blending run logs parameters, metrics, artifact paths to MLflow.", "Feature: context-v1 · Dataset: demo-grid-v1"],
            ["Model versioning", "Trust meta-model versions tracked. Stage: Staging → Production via benchmark validation.", "Version: 0.1.0 — heuristic contextual prior"],
            ["Artifact registry", "Model weights, feature configs, calibration versions stored. Reproducible forecasts.", "MLflow server: http://localhost:5001 (optional)"],
            ["Continuous learning", "Skill memory update → optional meta-model retrain on schedule. No huge retraining per observation.", "Next: online learning extension point"],
          ].map(([title, desc, hint]) => (
            <div key={title as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium text-cyan-300 mb-1">{title as string}</div>
              <div className="text-slate-400 text-xs leading-relaxed mb-2">{desc as string}</div>
              <div className="text-[11px] text-slate-500">{hint as string}</div>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
