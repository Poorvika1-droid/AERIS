import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070b14",
          900: "#0b1220",
          800: "#111b2e",
          700: "#1a2740",
        },
        accent: {
          cyan: "#22d3ee",
          green: "#34d399",
        },
      },
      fontFamily: {
        sans: ["var(--font-ui)", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
