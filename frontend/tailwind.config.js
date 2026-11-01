/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: '#1B1F4B',
        accent: {
          DEFAULT: '#3B3FD8',
          soft: '#EEF0FF',
        },
        text: '#1F2340',
        muted: '#6B7090',
        border: '#E3E5F2',
        page: '#F4F5FB',
        success: {
          DEFAULT: '#16A34A',
          soft: '#E9F8EF',
          border: '#BDE8CD',
        },
        warning: {
          DEFAULT: '#B45309',
          soft: '#FFF4DB',
        },
        placeholder: '#A0A4C0',
        field: '#F8F9FF',
      },
      fontFamily: {
        sans: ['Inter', 'Arial', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        btn: '10px',
      },
      fontSize: {
        'page-title': ['28px', { lineHeight: '1.2', fontWeight: '700' }],
        'card-title': ['16px', { lineHeight: '1.2', fontWeight: '700' }],
        'base': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'sm': ['13px', { lineHeight: '1.4' }],
        'xs': ['12px', { lineHeight: '1.3' }],
      }
    },
  },
  plugins: [],
}