"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

const DEMO_SESSION_KEY = "aeris-demo-session";
const PUBLIC_PATHS = new Set(["/", "/login", "/architecture", "/about"]);

// Called by Shell's logout button — sets a flag the login page reads
export function signOut(router: ReturnType<typeof useRouter>) {
  sessionStorage.removeItem(DEMO_SESSION_KEY);
  sessionStorage.setItem("aeris-just-logged-out", "1");
  router.replace("/login");
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 2,
            retryDelay: 1000,
            // A seed refresh briefly replaces the benchmark data. Polling makes
            // every open view recover automatically when that refresh completes.
            refetchInterval: 10_000,
            refetchOnWindowFocus: true,
          },
        },
      }),
  );
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (PUBLIC_PATHS.has(pathname)) {
      setChecked(true);
      return;
    }
    if (sessionStorage.getItem(DEMO_SESSION_KEY) === "authenticated") {
      setChecked(true);
      return;
    }
    router.replace("/login");
  }, [pathname, router]);

  if (!checked && !PUBLIC_PATHS.has(pathname)) return null;
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}
