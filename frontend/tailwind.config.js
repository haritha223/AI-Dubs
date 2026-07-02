/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        'fade-in-up': {
          '0%':   { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%':   { opacity: '0', transform: 'scale(0.92)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'slide-in-right': {
          '0%':   { opacity: '0', transform: 'translateX(32px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-8px)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(99,102,241,0.2)' },
          '50%':      { boxShadow: '0 0 40px rgba(99,102,241,0.5), 0 0 60px rgba(168,85,247,0.2)' },
        },
        'gradient-shift': {
          '0%':   { backgroundPosition: '0% 50%' },
          '50%':  { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'bounce-subtle': {
          '0%, 100%': { transform: 'translateY(-2px)' },
          '50%':      { transform: 'translateY(2px)' },
        },
        'spin-slow': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'pulse-slow':      'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in-up':      'fade-in-up 0.6s ease-out forwards',
        'fade-in-up-d1':   'fade-in-up 0.6s 0.1s ease-out both',
        'fade-in-up-d2':   'fade-in-up 0.6s 0.2s ease-out both',
        'fade-in-up-d3':   'fade-in-up 0.6s 0.3s ease-out both',
        'fade-in-up-d4':   'fade-in-up 0.6s 0.4s ease-out both',
        'fade-in-up-d5':   'fade-in-up 0.6s 0.5s ease-out both',
        'fade-in-up-d6':   'fade-in-up 0.6s 0.6s ease-out both',
        'fade-in':         'fade-in 0.5s ease-out forwards',
        'scale-in':        'scale-in 0.4s ease-out forwards',
        'slide-in-right':  'slide-in-right 0.5s ease-out forwards',
        'shimmer':         'shimmer 2.5s linear infinite',
        'float':           'float 4s ease-in-out infinite',
        'glow-pulse':      'glow-pulse 3s ease-in-out infinite',
        'gradient-shift':  'gradient-shift 6s ease infinite',
        'bounce-subtle':   'bounce-subtle 2s ease-in-out infinite',
        'spin-slow':       'spin-slow 12s linear infinite',
      },
    },
  },
  plugins: [],
}
