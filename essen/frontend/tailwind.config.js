/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'media',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#effaf3', 100: '#d8f3e1', 200: '#b4e6c7', 300: '#82d2a5', 400: '#4eb87f',
          500: '#2c9c63', 600: '#1e7f4f', 700: '#196642', 800: '#175137', 900: '#14432f',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,23,42,.04), 0 4px 16px rgba(15,23,42,.06)',
      },
    },
  },
  plugins: [],
}
