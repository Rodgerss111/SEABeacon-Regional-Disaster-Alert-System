import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        seabeacon: {
          panel: "#0e141b",
          panelLight: "#161e27",
          border: "#243044",
          text: "#e6edf3",
          dim: "#7d8590",
        },
      },
    },
  },
  plugins: [],
};

export default config;
