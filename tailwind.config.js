module.exports = {
  content: ["./**/*.html", "./**/*.js", "./**/*.py"],
  theme: {
    extend: {
      colors: {
        // Palette projet (option : calée sur tokens via inline rgba)
        brand: {
          50:  "#eef5ff",
          100: "#dceaff",
          200: "#b8d4ff",
          300: "#92bdff",
          400: "#6ba4ff",
          500: "#3a82ff",
          600: "#2563eb",  // bleu principal
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a"
        },
        success: "#16a34a",
        warning: "#f59e0b",
        danger:  "#ef4444"
      },
      boxShadow: {
        card: "0 8px 30px rgba(0,0,0,.06)"
      },
      borderRadius: {
        xl: "14px",
        "2xl": "20px"
      }
    }
  },
  darkMode: 'class',
  plugins: []
}
