/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: [{
      light: {
        "primary": "#0ea5e9",
        "secondary": "#64748b", 
        "accent": "#06b6d4",
        "neutral": "#1e293b",
        "base-100": "#ffffff",
        "base-200": "#f8fafc",
        "base-300": "#e2e8f0",
        "info": "#0ea5e9",
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
      }
    }, "dark"],
    base: true,
    styled: true,
    utils: true,
  },
}