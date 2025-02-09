#!/bin/bash

# Create a temporary directory for DMG contents
temp_dir="$(mktemp -d)/Yubikey SSH Manager"
mkdir -p "$temp_dir"

# Copy the app bundle
cp -r "dist/Yubikey SSH Manager.app" "$temp_dir/"

# Copy the installation script and requirements
cp install.sh "$temp_dir/"
cp requirements.txt "$temp_dir/"

# Create a README for the DMG
cat > "$temp_dir/README.txt" << EOL
Yubikey SSH Manager Installation

1. Open Terminal
2. Drag the install.sh script into the Terminal window
3. Press Enter to run the installation
4. Once installation is complete, you can run Yubikey SSH Manager.app

Note: The installation script will install:
- Homebrew (if not already installed)
- Python 3.9
- Required Python packages
- Yubikey tools

For more information, visit: https://github.com/robertherbaugh/yubikey-ssh-manager
EOL

# Create the DMG
create-dmg \
  --volname "Yubikey SSH Manager" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "Yubikey SSH Manager.dmg" \
  "$temp_dir"
