/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef7ff', 100: '#d9ecff', 200: '#b9d9ff', 300: '#89bdff',
          400: '#5298ff', 500: '#2b76f6', 600: '#1658dc', 700: '#1447b0',
          800: '#173d8c', 900: '#193671',
        },
        ink: { 900: '#111827', 700: '#334155', 500: '#64748b' },
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
      boxShadow: { card: '0 1px 2px rgba(16,24,40,.06), 0 8px 24px rgba(16,24,40,.05)' },
    },
  },
  plugins: [],
}
