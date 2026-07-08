/** @type {import('tailwindcss').Config} */
import plugin from 'tailwindcss/plugin'

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Refined dark "instrument" surface. Warm near-black with cool slate
        // panels — deliberately not the flat #000-ish + single-accent default.
        surface: {
          DEFAULT: '#0E1117',
          raised: '#161A22',
          sunken: '#0A0D12',
          muted: '#1C212B',
          hover: '#262C38',
          line: '#232A36',
        },
        ink: {
          DEFAULT: '#ECEFF4',
          soft: '#C7CEDA',
          muted: '#98A2B3',
          faint: '#6B7686',
          ghost: '#434C5C',
        },
        // Primary signal: indigo. Carries actions, focus, the logo rail.
        brand: {
          50: '#EEF0FF',
          100: '#DADEFF',
          200: '#B7BEFF',
          300: '#9098FB',
          400: '#6366F1',
          500: '#5147E0',
          600: '#4338CA',
          700: '#372FA6',
          800: '#2C2682',
          900: '#1F1B5C',
        },
        // Secondary signal: amber. Reserved for data emphasis / measurement.
        accent: {
          50: '#FEF6E7',
          100: '#FCE7B8',
          200: '#F8D182',
          300: '#F0A92B',
          400: '#DB9215',
          500: '#B8770C',
          600: '#925E0B',
          700: '#73490C',
          800: '#56380D',
          900: '#3A2609',
        },
        danger: {
          50: '#FFF1F2',
          500: '#F43F5E',
          700: '#BE123C',
        },
      },
      fontFamily: {
        display: ['Space Grotesk', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      letterSpacing: {
        tight: '0em',
        normal: '0em',
        wide: '0.025em',
        wider: '0.05em',
        widest: '0.08em',
      },
      borderRadius: {
        lg: '0.5rem',
        xl: '0.625rem',
        '2xl': '0.75rem',
        '3xl': '1rem',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(0,0,0,0.28), 0 8px 24px rgba(0,0,0,0.18)',
        card: '0 1px 0 rgba(255,255,255,0.04) inset, 0 16px 42px rgba(0,0,0,0.22)',
        raised: '0 24px 70px rgba(0,0,0,0.34), 0 4px 16px rgba(0,0,0,0.26)',
        float: '0 30px 90px rgba(0,0,0,0.48), 0 10px 28px rgba(0,0,0,0.34)',
        glow: '0 0 0 1px rgba(99,102,241,0.35), 0 18px 54px rgba(99,102,241,0.16)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(24px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slide: {
          '0%': { transform: 'translateX(-100%)' },
          '50%': { transform: 'translateX(120%)' },
          '100%': { transform: 'translateX(320%)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
        typing: {
          '0%, 100%': { transform: 'translateY(0)', opacity: '0.35' },
          '50%': { transform: 'translateY(-3px)', opacity: '1' },
        },
        caret: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.98)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.28s ease-out both',
        'fade-up': 'fade-up 0.34s cubic-bezier(0.23,1,0.32,1) both',
        'slide-in-right': 'slide-in-right 0.34s cubic-bezier(0.23,1,0.32,1) both',
        slide: 'slide 1.4s ease-in-out infinite',
        'pulse-soft': 'pulse-soft 1.6s ease-in-out infinite',
        typing: 'typing 1.1s ease-in-out infinite',
        caret: 'caret 1s step-end infinite',
        'scale-in': 'scale-in 0.22s cubic-bezier(0.23,1,0.32,1) both',
      },
      transitionTimingFunction: {
        smooth: 'cubic-bezier(0.23,1,0.32,1)',
      },
    },
  },
  plugins: [
    plugin(({ addUtilities }) => {
      const delays = [75, 150, 200, 300, 400, 500, 700]
      const utils = {}
      delays.forEach((d) => {
        utils[`.animation-delay-${d}`] = { 'animation-delay': `${d}ms` }
      })
      addUtilities(utils)
    }),
  ],
}