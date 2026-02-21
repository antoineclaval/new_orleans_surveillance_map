/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './nola_cameras/templates/**/*.html',
    './nola_cameras/static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        nola: {
          purple: '#6b46c1',
          gold: '#d69e2e',
        }
      }
    },
  },
  plugins: [],
}
