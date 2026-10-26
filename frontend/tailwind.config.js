/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      keyframes: {
        indeterminate: {
          "0%": { transform: "translateX(-100%) scaleX(0.4)" },
          "50%": { transform: "translateX(40%) scaleX(0.6)" },
          "100%": { transform: "translateX(250%) scaleX(0.4)" },
        },
      },
    },
  },
  plugins: [],
};
