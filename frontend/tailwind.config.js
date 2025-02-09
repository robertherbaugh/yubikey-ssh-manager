/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'yubikey-blue': '#284c7e',
        'yubikey-green': '#9aca3c',
      },
    },
  },
  plugins: [],
}
