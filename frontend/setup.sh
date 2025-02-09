#!/bin/bash

# Install dependencies
npm install

# Create necessary directories
mkdir -p static/css static/img

# Initialize postcss config
echo "module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  }
}" > postcss.config.js

# Build Tailwind CSS
npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css

# Start watching for changes
echo "Setup complete! Run 'npm run build' to start watching for CSS changes."
