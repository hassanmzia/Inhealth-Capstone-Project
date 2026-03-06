import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'

const config: Config = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        // Medical Blue — primary brand color
        primary: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#1d6fdb',
          700: '#1a5fc8',
          800: '#1e4fa6',
          900: '#1e3a8a',
          950: '#172554',
          DEFAULT: '#1d6fdb',
          foreground: '#ffffff',
        },
        // Health Green — secondary / success
        secondary: {
          50:  '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
          DEFAULT: '#16a34a',
          foreground: '#ffffff',
        },
        // Clinical Red — danger / critical
        danger: {
          50:  '#fff1f2',
          100: '#ffe4e6',
          200: '#fecdd3',
          300: '#fda4af',
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
          700: '#be123c',
          800: '#9f1239',
          900: '#881337',
          950: '#4c0519',
          DEFAULT: '#e11d48',
          foreground: '#ffffff',
        },
        // Alert Amber — warning
        warning: {
          50:  '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
          950: '#451a03',
          DEFAULT: '#d97706',
          foreground: '#ffffff',
        },
        // Neutral clinical grays
        clinical: {
          50:  '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        // shadcn/ui compatible tokens
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'alert-pulse': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.05)' },
        },
        'vitals-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(29, 111, 219, 0.4)' },
          '50%': { boxShadow: '0 0 0 8px rgba(29, 111, 219, 0)' },
        },
        'critical-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(225, 29, 72, 0.5)' },
          '50%': { boxShadow: '0 0 0 10px rgba(225, 29, 72, 0)' },
        },
        'agent-spin': {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
        'slide-in-right': {
          from: { transform: 'translateX(100%)', opacity: '0' },
          to: { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-in-up': {
          from: { transform: 'translateY(20px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          from: { transform: 'translateY(-8px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'count-up': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        'gradient-flow': {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        'scale-in': {
          from: { transform: 'scale(0.95)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'alert-pulse': 'alert-pulse 2s ease-in-out infinite',
        'vitals-pulse': 'vitals-pulse 2s ease-in-out infinite',
        'critical-pulse': 'critical-pulse 1.5s ease-in-out infinite',
        'agent-spin': 'agent-spin 1s linear infinite',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'slide-in-up': 'slide-in-up 0.3s ease-out',
        'slide-down': 'slide-down 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'count-up': 'count-up 0.5s ease-out',
        shimmer: 'shimmer 2s linear infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'gradient-flow': 'gradient-flow 6s ease infinite',
        'scale-in': 'scale-in 0.2s ease-out',
      },
      backgroundImage: {
        'gradient-clinical': 'linear-gradient(135deg, #1d6fdb 0%, #1a5fc8 50%, #1e3a8a 100%)',
        'gradient-health': 'linear-gradient(135deg, #16a34a 0%, #15803d 100%)',
        'gradient-danger': 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
        'gradient-mesh': 'radial-gradient(at 40% 20%, #3b82f6 0px, transparent 50%), radial-gradient(at 80% 0%, #06b6d4 0px, transparent 50%), radial-gradient(at 0% 50%, #8b5cf6 0px, transparent 50%), radial-gradient(at 80% 50%, #ec4899 0px, transparent 50%), radial-gradient(at 0% 100%, #14b8a6 0px, transparent 50%)',
        'gradient-sidebar': 'linear-gradient(180deg, hsl(var(--sidebar-from)) 0%, hsl(var(--sidebar-to)) 100%)',
        'gradient-vibrant': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'gradient-ocean': 'linear-gradient(135deg, #0ea5e9 0%, #3b82f6 50%, #8b5cf6 100%)',
        'gradient-sunset': 'linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #ec4899 100%)',
        'gradient-forest': 'linear-gradient(135deg, #22c55e 0%, #14b8a6 50%, #0ea5e9 100%)',
        shimmer: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%)',
      },
      boxShadow: {
        clinical: '0 4px 6px -1px rgba(29, 111, 219, 0.1), 0 2px 4px -1px rgba(29, 111, 219, 0.06)',
        'clinical-lg': '0 10px 15px -3px rgba(29, 111, 219, 0.1), 0 4px 6px -2px rgba(29, 111, 219, 0.05)',
        alert: '0 0 0 3px rgba(225, 29, 72, 0.15)',
        card: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.02)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.06), 0 12px 28px rgba(0,0,0,0.04)',
        'card-elevated': '0 8px 24px rgba(0,0,0,0.06), 0 20px 48px rgba(0,0,0,0.04)',
        glass: '0 8px 32px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        'glass-dark': '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        glow: '0 0 20px rgba(59, 130, 246, 0.15)',
        'glow-lg': '0 0 40px rgba(59, 130, 246, 0.2)',
        'inner-glow': 'inset 0 1px 0 rgba(255, 255, 255, 0.1)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [animate],
}

export default config
