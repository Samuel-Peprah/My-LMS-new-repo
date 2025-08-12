/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  safelist: [
    'text-red-600',
    'text-yellow-500',
    'text-green-600'
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
