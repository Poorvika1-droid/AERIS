import { Shell, Card } from "@/components/shell";
import Link from "next/link";

const DIFFERENTIATORS = [
  {
    n: "01",
    title: "Context-aware dynamic weighting",
    desc: "Trust is not static. Every weight is a function of geographic region, forecast lead time, season, weather regime, transition probability, recent skill, model health, and inter-model disagreement.",
    color: "#22d3ee",
  },
  {
    n: "02",
    title: "Model health monitoring",
    desc: "Completeness, run delay, outlier rate, distribution shift, and verification degradation are tracked continuously. A degraded model's weight is automatically reduced before the blend.",
    color: "#34d399",
  },
  {
    n: "03",
    title: "Forecast disagreement intelligence",
    desc: "When models disagree significantly, the ensemble's weight increases and the Forecast Reliability Score drops. Disagreement is surfaced as a decision-support signal, not hidden.",
    color: "#a78bfa",
  },
  {
    n: "04",
    title: "Extreme-event-aware blending",
    desc: "Normal weather and extreme weather use different objectives. Heavy rainfall uses CSI, Brier score, and event-detection weighting. Configurable thresholds — not official warning thresholds.",
    color: "#fbbf24",
  },
  {
    n: "05",
    title: "Explainable forecast intelligence",
    desc: "Every AERIS forecast includes WHY: which model contributed, what weight, under what regime, and why — with rule-based attribution (SHAP optional when meta-model is fully trained).",
    color: "#fb7185",
  },
  {
    n: "06",
    title: "Continuous self-learning",
    desc: "Forecast → Observation → Error → Skill update → Weight recalibration. The system learns from every verified forecast. Rolling windows: 7d, 30d, 90d, seasonal, historical.",
    color: "#f97316",
  },
];

const ADVANCED = [
  {
    n: "07",
    title: "Counterfactual forecasting",
    desc: "Simulation lab: remove a model, boost a weight, switch strategy, compare outcomes. Production state is never mutated.",
  },
  {
    n: "08",
    title: "Forecast failure risk",
    desc: "Predicts whether the current consensus may be unreliable. Decision-support indicator — not a claim of certain failure.",
  },
  {
    n: "09",
    title: "Spatially coherent blending",
    desc: "Gaussian smoothing on weight fields prevents noisy grid-by-grid maps without suppressing extreme-event signals.",
  },
  {
    n: "10",
    title: "Plug-and-play model ecosystem",
    desc: "Any new forecast source implementing BaseForecastAdapter is automatically evaluated and registered. No engine change.",
  },
  {
    n: "11",
    title: "Observation-aware correction",
    desc: "Bias correction hooks at harmonization stage. Rolling bias statistics per model × region × variable.",
  },
  {
    n: "12",
    title: "National-scale operational path",
    desc: "Architecture is horizontally scalable. Docker Compose → Kubernetes. REST APIs + adapter pattern allow region-by-region rollout.",
  },
];

export default function AboutPage() {
  return (
    <Shell>
      {/* Hero */}
      <div className="mb-10 max-w-4xl">
        <div className="text-xs tracking-[0.3em] text-cyan-400 mb-2">SIH 2026 · PS 26081 · MoES / NCMRWF · Disaster Management</div>
        <h1 className="text-3xl font-semibold text-white leading-tight">
          AERIS — Adaptive Ensemble &amp; Regime Intelligence System
        </h1>
        <p className="mt-3 text-lg text-slate-300 leading-relaxed">
          Hybrid AI–NWP multi-model forecast blending for a safer, climate-resilient India.
        </p>
        <p className="mt-3 text-sm text-slate-400 leading-relaxed max-w-3xl">
          AERIS does not replace NWP or train an enormous global weather foundation model.
          It answers a precise operational question:{" "}
          <em className="text-slate-300">
            "Which forecast source should be trusted, by how much, where, when, and under what atmospheric conditions?"
          </em>
        </p>
        <div className="mt-4 rounded border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-200 max-w-2xl">
          Prototype for SIH 2026 PS 26081. Demonstration / Benchmark Data unless operational adapters are configured.
          Not a claim of NCMRWF deployment, endorsement, or guaranteed skill improvement.
        </div>
      </div>

      {/* Core messages */}
      <Card title="Core messages" className="mb-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            "One forecast is not always enough.",
            "The best model changes with context.",
            "AERIS learns when, where and why each model should be trusted.",
            "Forecast uncertainty is information, not a failure.",
            "Every verified forecast improves future model trust.",
          ].map((msg, i) => (
            <div key={i} className="rounded border border-cyan-900/30 bg-navy-900/60 px-3 py-2">
              <div className="text-[11px] text-cyan-400 mb-1">0{i + 1}</div>
              <div className="text-sm text-slate-300 leading-relaxed">{msg}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Architecture pipeline */}
      <Card title="Architecture — Context-Aware Forecast Trust Engine" className="mb-6">
        <div className="overflow-x-auto">
          <div className="flex items-center gap-1 text-xs min-w-max py-2">
            {[
              ["Forecast sources", "#22d3ee"],
              ["→", "#475569"],
              ["Data harmonization", "#22d3ee"],
              ["→", "#475569"],
              ["Quality control", "#22d3ee"],
              ["→", "#475569"],
              ["Context engine", "#34d399"],
              ["→", "#475569"],
              ["Skill memory", "#34d399"],
              ["→", "#475569"],
              ["Health monitor", "#fbbf24"],
              ["→", "#475569"],
              ["Trust engine", "#f59e0b"],
              ["→", "#475569"],
              ["Adaptive blending", "#a78bfa"],
              ["→", "#475569"],
              ["Uncertainty", "#a78bfa"],
              ["→", "#475569"],
              ["Extreme events", "#fb7185"],
              ["→", "#475569"],
              ["Verification", "#22d3ee"],
              ["→", "#475569"],
              ["Recalibration ↺", "#34d399"],
            ].map(([label, color], i) => (
              <div key={i} className="shrink-0">
                {label === "→" ? (
                  <span style={{ color: color as string }} className="mx-0.5">{label}</span>
                ) : (
                  <div
                    className="rounded border px-2 py-1 font-medium"
                    style={{
                      color: color as string,
                      borderColor: (color as string) + "44",
                      background: (color as string) + "11",
                    }}
                  >
                    {label as string}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Every dashboard surface consumes outputs from the Context-Aware Forecast Trust Engine.
          No disconnected features — everything traces back to the central intelligence engine.
        </p>
      </Card>

      {/* 6 core differentiators */}
      <h2 className="text-lg font-semibold text-white mb-4">Why AERIS? — 6 core differentiators</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-6">
        {DIFFERENTIATORS.map((d) => (
          <div
            key={d.n}
            className="rounded-lg border bg-navy-800 px-4 py-4 hover:bg-navy-700/60 transition-colors"
            style={{ borderColor: d.color + "33" }}
          >
            <div className="text-[11px] font-mono mb-2" style={{ color: d.color }}>{d.n}</div>
            <h3 className="font-semibold text-white mb-2">{d.title}</h3>
            <p className="text-sm text-slate-400 leading-relaxed">{d.desc}</p>
          </div>
        ))}
      </div>

      {/* Advanced / future */}
      <h2 className="text-lg font-semibold text-white mb-4">Advanced features &amp; future scope</h2>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 mb-6">
        {ADVANCED.map((d) => (
          <div key={d.n} className="rounded border border-white/5 bg-navy-800 px-4 py-3">
            <div className="text-[11px] font-mono text-slate-500 mb-1">{d.n}</div>
            <h3 className="font-medium text-cyan-300 mb-1">{d.title}</h3>
            <p className="text-xs text-slate-400 leading-relaxed">{d.desc}</p>
          </div>
        ))}
      </div>

      {/* Scientific honesty */}
      <Card title="Scientific honesty &amp; limitations" className="mb-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">What this IS</div>
            <ul className="space-y-1 text-slate-300 text-xs">
              {[
                "A prototype blending framework designed for NCMRWF integration",
                "Demonstration of context-aware dynamic weighting principles",
                "Architecture designed for operational-scale extension",
                "A vehicle for scientific discussion of hybrid AI–NWP blending",
                "An open, reproducible benchmark for ensemble blending approaches",
              ].map((t) => <li key={t} className="flex gap-1.5"><span className="text-green-400">✓</span>{t}</li>)}
            </ul>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-2">What this IS NOT</div>
            <ul className="space-y-1 text-slate-300 text-xs">
              {[
                "Not a deployment at NCMRWF or any operational centre",
                "Not trained on real NCMRWF operational archives",
                "Not endorsed by Ministry of Earth Sciences or IMD",
                "Benchmark metrics are NOT real operational accuracy claims",
                "Regime labels are operational weighting classes, not official taxonomies",
                "FRS is a decision-support summary, not a universal scientific metric",
              ].map((t) => <li key={t} className="flex gap-1.5"><span className="text-amber-400">⚠</span>{t}</li>)}
            </ul>
          </div>
        </div>
      </Card>

      {/* Technology stack */}
      <Card title="Technology stack">
        <div className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Frontend", "Next.js 15 · React 19 · TypeScript · Tailwind CSS · shadcn/ui · Lucide · MapLibre GL · Recharts · TanStack Query · Zod · React Hook Form · Framer Motion"],
            ["Backend", "Python · FastAPI · Pydantic v2 · SQLAlchemy 2 · MySQL / SQLite · Redis · Celery · WebSockets"],
            ["Data / Science", "NumPy · pandas · xarray · SciPy · scikit-learn · XGBoost · LightGBM · Optuna · statsmodels · netCDF4 · Zarr"],
            ["MLOps / Infra", "MLflow · Docker Compose · GitHub Actions · MySQL · structured logging · Kubernetes-ready architecture"],
          ].map(([title, libs]) => (
            <div key={title as string} className="rounded border border-white/5 bg-navy-900/60 px-3 py-2">
              <div className="font-medium text-cyan-300 mb-2">{title as string}</div>
              <div className="text-slate-400 leading-relaxed">{libs as string}</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="mt-6 text-center">
        <Link
          href="/overview"
          className="inline-block rounded bg-cyan-500 px-6 py-2.5 text-sm font-semibold text-navy-950 hover:bg-cyan-400 transition-colors"
        >
          Open operations console →
        </Link>
      </div>
    </Shell>
  );
}
