import typography from "@tailwindcss/typography";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        display: ['"Instrument Sans"', "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          950: "#0c0e14",
          900: "#12151f",
          800: "#1a1f2e",
        },
      },
      boxShadow: {
        glow: "0 0 80px -20px rgba(99, 102, 241, 0.45)",
      },
    },
  },
  plugins: [typography],
};
