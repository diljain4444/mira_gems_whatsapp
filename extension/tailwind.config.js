/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{ts,tsx,html}', './sidepanel.html'],
  theme: {
    extend: {
      colors: {
        bg:           '#0A0A0F',
        surface:      '#12121A',
        surface2:     '#1A1A28',
        border:       '#2A2A3F',
        accent:       '#C4A35A',
        'accent-light': '#E8D5A3',
        text:         '#E8E8F0',
        muted:        '#8888A8',
        available:    '#4CAF50',
        memo:         '#FF9800',
        hold:         '#F44336',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 2.5s ease-in-out infinite',
        'spin-slow':  'spin 2s linear infinite',
      },
    },
  },
  plugins: [],
}
