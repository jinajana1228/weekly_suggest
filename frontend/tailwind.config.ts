import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          base: "#09090B",
          surface: "#111113",
          elevated: "#18181B",
          overlay: "#1E1E23",
        },
        border: {
          default: "#27272A",
          subtle: "#1E1E23",
        },
        text: {
          primary: "#FAFAFA",
          secondary: "#A1A1AA",
          muted: "#52525B",
        },
        accent: {
          blue: "#3B82F6",
          gold: "#F59E0B",
          red: "#EF4444",
          green: "#22C55E",
          gray: "#71717A",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
