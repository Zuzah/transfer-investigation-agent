import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // Wealthsimple brand palette — mirrors :root vars in the original style.css.
      colors: {
        dune:       "#32302F",
        gold:       "#ECD06F",
        "gray-ws":  "#9C9C9C",
        light:      "#F7F6F4",
        "ws-border":"#E8E6E1",
        "ws-red":   "#C0392B",
      },
    },
  },
  plugins: [],
};

export default config;
