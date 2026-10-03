"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  ChartNoAxesCombined,
  BookOpen,
  Boxes,
  CloudRain,
  Database,
  GitCompare,
  Globe,
  HeartPulse,
  Layers,
  LayoutDashboard,
  LogOut,
  Map,
  Scale,
  Server,
  ShieldAlert,
  Sparkles,
  User,
} from "lucide-react";
import { cn } from "@/lib/api";
import { signOut } from "@/components/providers";

const NAV = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/forecast", label: "Forecast Explorer", icon: CloudRain },
  { href: "/gis", label: "India GIS", icon: Map },
  { href: "/weights", label: "Model Weight Maps", icon: Layers },
  { href: "/model-health", label: "Model Health", icon: HeartPulse },
  { href: "/regimes", label: "Weather Regimes", icon: Activity },
  { href: "/events", label: "Extreme Events", icon: AlertTriangle },
  { href: "/uncertainty", label: "Uncertainty & FRS", icon: ShieldAlert },
  { href: "/lab", label: "Counterfactual Lab", icon: GitCompare },
  { href: "/verification", label: "Verification", icon: Scale },
  { href: "/data", label: "Data Hub", icon: Database },
  { href: "/registry", label: "Model Registry", icon: Boxes },
  { href: "/system", label: "System Health", icon: Server },
  { href: "/integration", label: "API / Integration", icon: Globe },
  { href: "/about", label: "About AERIS", icon: BookOpen },
  { href: "/architecture", label: "AERIS Flow", icon: ChartNoAxesCombined },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    signOut(router);
  };

  return (
    <div className="min-h-screen bg-navy-950 text-slate-200">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-[240px] flex-col border-r border-cyan-900/30 bg-navy-900">
        <Link href="/" className="border-b border-cyan-900/30 px-4 py-4">
          <div className="text-xs tracking-[0.28em] text-cyan-400">MOES · NCMRWF · SIH 2026</div>
          <div className="mt-1 font-semibold text-white">AERIS</div>
          <div className="text-[11px] text-slate-400">Forecast Trust Engine</div>
        </Link>
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {NAV.map((item) => {
            const active = path === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "mb-0.5 flex items-center gap-2 rounded px-2 py-1.5 text-[13px]",
                  active ? "bg-cyan-500/15 text-cyan-200" : "text-slate-400 hover:bg-white/5 hover:text-slate-100",
                )}
              >
                <Icon size={14} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        {/* User + logout footer */}
        <div className="border-t border-cyan-900/30 p-3">
          <div className="flex items-center gap-2 rounded-lg bg-white/5 px-2 py-2">
            <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-cyan-400/20 text-cyan-300">
              <User size={13} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] font-medium text-slate-200">demo@aeris.local</div>
              <div className="text-[10px] text-slate-500">Analyst · read-only</div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="shrink-0 rounded p-1 text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition-colors"
            >
              <LogOut size={13} />
            </button>
          </div>
          <div className="mt-2 text-[10px] text-slate-600">Prototype · not operational</div>
        </div>
      </aside>
      <div className="ml-[240px] min-h-screen">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-cyan-900/30 bg-navy-950/90 px-6 py-3 backdrop-blur">
          <div className="flex items-center gap-2 text-xs text-amber-200/90">
            <Sparkles size={14} />
            Demonstration / Benchmark Data — not NCMRWF operational archives
          </div>
          <div className="flex items-center gap-4">
            <div className="font-mono text-[11px] text-slate-500">PS 26081 · Disaster Management</div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-white/5 px-3 py-1.5 text-[12px] text-slate-400 hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-400 transition-colors"
            >
              <LogOut size={12} />
              Sign out
            </button>
          </div>
        </header>
        <main className="px-6 py-5">{children}</main>
      </div>
    </div>
  );
}

export function Card({ title, children, className }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-lg border border-cyan-900/30 bg-navy-800 p-4", className)}>
      {title ? <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h2> : null}
      {children}
    </section>
  );
}

export function Kpi({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border border-cyan-900/25 bg-navy-800 px-3 py-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-white">{value}</div>
      {hint ? <div className="mt-1 text-[11px] text-slate-500">{hint}</div> : null}
    </div>
  );
}
