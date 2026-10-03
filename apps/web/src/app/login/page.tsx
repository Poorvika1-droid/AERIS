"use client";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CloudRain, Eye, EyeOff, LockKeyhole, ShieldCheck, Waves } from "lucide-react";

const DEMO_EMAIL = "demo@aeris.local";
const DEMO_PASSWORD = "aeris-demo-2026";
const SESSION_KEY = "aeris-demo-session";

export default function LoginPage() {
  const [email, setEmail] = useState(DEMO_EMAIL);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loggedOut, setLoggedOut] = useState(false);
  const router = useRouter();

  // Detect if user was redirected here after logout
  useEffect(() => {
    if (typeof window !== "undefined") {
      const wasAuth = sessionStorage.getItem("aeris-just-logged-out");
      if (wasAuth === "1") {
        setLoggedOut(true);
        sessionStorage.removeItem("aeris-just-logged-out");
      }
    }
  }, []);

  const signIn = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    // Simulate brief auth check
    setTimeout(() => {
      if (
        email.trim().toLowerCase() !== DEMO_EMAIL ||
        password !== DEMO_PASSWORD
      ) {
        setError("Invalid credentials. Use the demo account shown below.");
        setLoading(false);
        return;
      }
      sessionStorage.setItem(SESSION_KEY, "authenticated");
      router.replace("/overview");
    }, 600);
  };

  return (
    <main className="aeris-grid grid min-h-screen place-items-center bg-navy-950 p-4 text-slate-100">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-cyan-400/20 bg-navy-900 shadow-2xl shadow-cyan-950/40 md:grid-cols-[1.15fr_0.85fr]">

        {/* ─── Left panel ─── */}
        <section className="relative hidden min-h-[640px] overflow-hidden border-r border-cyan-400/10 p-10 md:flex md:flex-col">
          {/* Background glow */}
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_25%,rgba(34,211,238,.18),transparent_40%),radial-gradient(circle_at_75%_80%,rgba(52,211,153,.12),transparent_35%)]" />
          <div className="pointer-events-none absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTAgMCBMNjAgMCBMNjAgNjAgTDAgNjAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgzNCwyMTEsMjM4LDAuMDQpIiBzdHJva2Utd2lkdGg9IjEiLz48L3N2Zz4=')] opacity-40" />

          <div className="relative flex-1 flex flex-col">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 text-cyan-200 hover:text-cyan-100 transition-colors w-fit">
              <div className="grid h-9 w-9 place-items-center rounded-xl border border-cyan-300/30 bg-cyan-400/10">
                <Waves size={18} />
              </div>
              <div>
                <div className="font-bold tracking-[.22em] text-white text-sm">AERIS</div>
                <div className="text-[10px] tracking-[.15em] text-cyan-300/70">FORECAST INTELLIGENCE</div>
              </div>
            </Link>

            {/* Tagline */}
            <div className="mt-16">
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/5 px-3 py-1 text-[11px] text-cyan-300 mb-6">
                <CloudRain size={11} />
                SIH 2026 · PS 26081 · Disaster Management
              </div>
              <h1 className="text-4xl font-semibold leading-[1.1] text-white">
                Every forecast<br />
                deserves a<br />
                <span className="text-cyan-300">confidence story.</span>
              </h1>
              <p className="mt-5 text-sm leading-7 text-slate-400 max-w-xs">
                A decision-intelligence workspace for forecast analysts, disaster managers and research teams.
              </p>
            </div>

            {/* Feature bullets */}
            <div className="mt-12 space-y-3">
              {[
                "Context-aware adaptive model weighting",
                "Forecast Reliability Score per location",
                "Explainable trust with counterfactual lab",
                "Extreme-event intelligence & alerts",
              ].map((x) => (
                <div key={x} className="flex items-center gap-3 text-sm text-slate-300">
                  <ShieldCheck className="shrink-0 text-emerald-400" size={15} />
                  {x}
                </div>
              ))}
            </div>

            {/* Bottom badge */}
            <div className="mt-auto pt-10">
              <div className="rounded-2xl border border-white/5 bg-navy-950/60 px-4 py-3 text-xs text-slate-500">
                Ministry of Earth Sciences · NCMRWF · Prototype<br />
                Demonstration / Benchmark Data · not operational archives
              </div>
            </div>
          </div>
        </section>

        {/* ─── Right panel / form ─── */}
        <section className="flex flex-col justify-center px-8 py-10 sm:px-10">
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-2 text-cyan-200 md:hidden">
            <Waves size={20} />
            <span className="font-bold tracking-[.2em] text-sm">AERIS</span>
          </div>

          {/* Header */}
          <div className="mb-7">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-cyan-400/10 border border-cyan-300/20 text-cyan-200 mb-5">
              <LockKeyhole size={20} />
            </div>
            <h2 className="text-2xl font-semibold text-white">Welcome back</h2>
            <p className="mt-1.5 text-sm text-slate-400">
              Sign in to open the Forecast Intelligence Console
            </p>
          </div>

          {/* Logged-out notice */}
          {loggedOut && (
            <div className="mb-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              You have been signed out successfully.
            </div>
          )}

          {/* Demo credentials hint */}
          <div className="mb-5 rounded-xl border border-cyan-300/15 bg-cyan-300/5 px-4 py-3">
            <div className="text-[11px] font-medium tracking-wider text-cyan-400 mb-1.5">DEMO CREDENTIALS</div>
            <div className="text-xs text-slate-300 space-y-0.5">
              <div><span className="text-slate-500">Email</span> &nbsp; demo@aeris.local</div>
              <div><span className="text-slate-500">Password</span> &nbsp; aeris-demo-2026</div>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={signIn} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Work email
              </label>
              <input
                required
                type="email"
                value={email}
                autoComplete="email"
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-navy-950 px-4 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/20 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  required
                  type={showPassword ? "text" : "password"}
                  value={password}
                  autoComplete="current-password"
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-navy-950 px-4 py-2.5 pr-10 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/20 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-2.5 text-xs text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-bold text-navy-950 hover:bg-cyan-200 disabled:opacity-60 transition-colors mt-1"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-navy-900/30 border-t-navy-900" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in to console
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>

          {/* Footer links */}
          <div className="mt-6 flex items-center justify-between">
            <Link href="/architecture" className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">
              How AERIS works →
            </Link>
            <Link href="/about" className="text-xs text-slate-500 hover:text-slate-400 transition-colors">
              About the project
            </Link>
          </div>

          <p className="mt-8 text-center text-[10px] leading-5 text-slate-600">
            Demo authentication protects local console navigation only.<br />
            Not production identity management or a real credentials store.
          </p>
        </section>
      </div>
    </main>
  );
}
